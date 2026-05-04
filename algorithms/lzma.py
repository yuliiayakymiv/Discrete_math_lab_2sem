from collections import defaultdict, deque

HASH_LEN = 2
WINDOW_SIZE = 4096
MAX_LEN = 273
MAX_CANDIDATES = 32
PROB_INIT = 1024
PROB_MAX = 2048
MOVE_BITS = 5

class EndMarker:
    def __repr__(self):
        return "EndMarker()"

class BitModel:
    def __init__(self):
        self.prob = PROB_INIT  # ймовірність нуля

    def update(self, bit):
        if bit == 0:
            self.prob += (PROB_MAX - self.prob) >> MOVE_BITS
        else:
            self.prob -= self.prob >> MOVE_BITS
class ModelSet:
    def __init__(self):
        self.first = BitModel()
        self.second = BitModel()
        self.third = BitModel()
        self.fourth = BitModel()

        self.literal = [BitModel() for _ in range(8)]

        self.len_first = BitModel()
        self.len_second = BitModel()
        self.len_low = [BitModel() for _ in range(3)]
        self.len_mid = [BitModel() for _ in range(3)]
        self.len_high = [BitModel() for _ in range(8)]

        self.dist_first = BitModel()
        self.dist_second = BitModel()
        self.dist_low = [BitModel() for _ in range(4)]
        self.dist_mid = [BitModel() for _ in range(8)]
        self.dist_high = [BitModel() for _ in range(12)]

        self.rep_index = [BitModel() for _ in range(2)]


class RangeBitWriter:
    def __init__(self):
        self.encoder = RangeEncoder()
        self.models = ModelSet()

    def write_bit(self, model, bit):
        self.encoder.encode_bit(model, bit)

    def write_bits(self, value, count, models):
        for i in range(count):
            bit = (value >> (count - 1 - i)) & 1
            self.write_bit(models[i], bit)

    def finish(self):
        return self.encoder.finish()


class RangeBitReader2:
    def __init__(self, data):
        self.decoder = RangeDecoder(data)
        self.models = ModelSet()

    def read_bit(self, model):
        return self.decoder.decode_bit(model)

    def read_bits(self, count, models):
        value = 0
        for i in range(count):
            value = (value << 1) | self.read_bit(models[i])
        return value

class Literal:
    def __init__(self, byte):
        self.byte = byte

    def __repr__(self):
        return f"Literal({self.byte})"


class Match:
    def __init__(self, length, distance):
        self.length = length
        self.distance = distance

    def __repr__(self):
        return f"Match(length={self.length}, distance={self.distance})"


class ShortRep:
    def __repr__(self):
        return "ShortRep()"


class LongRep:
    def __init__(self, rep_index, length):
        self.rep_index = rep_index
        self.length = length

    def __repr__(self):
        return f"LongRep(rep{self.rep_index}, length={self.length})"

class RangeEncoder:
    def __init__(self):
        self.low = 0
        self.range = 0xFFFFFFFF
        self.out = bytearray()

        self.cache = 0
        self.cache_size = 1

    def encode_bit(self, model, bit):
        bound = (self.range >> 11) * model.prob

        if bit == 0:
            self.range = bound
        else:
            self.low += bound
            self.range -= bound

        model.update(bit)

        while self.range < 0x01000000:
            self.range <<= 8
            self._shift_low()

    def _shift_low(self):
        low_hi = self.low >> 32

        if self.low < 0xFF000000 or low_hi != 0:
            carry = low_hi & 0xFF

            self.out.append((self.cache + carry) & 0xFF)

            for _ in range(self.cache_size - 1):
                self.out.append((0xFF + carry) & 0xFF)

            self.cache = (self.low >> 24) & 0xFF
            self.cache_size = 0

        self.cache_size += 1
        self.low = (self.low & 0xFFFFFF) << 8

    def finish(self):
        for _ in range(5):
            self._shift_low()

        return bytes(self.out)

class RangeDecoder:
    def __init__(self, data):
        self.data = data
        self.pos = 0
        self.code = 0
        self.range = 0xFFFFFFFF

        for _ in range(5):
            self.code = (self.code << 8) | self._read_byte()

    def _read_byte(self):
        if self.pos < len(self.data):
            b = self.data[self.pos]
            self.pos += 1
            return b
        return 0

    def decode_bit(self, model):
        bound = (self.range >> 11) * model.prob

        if self.code < bound:
            bit = 0
            self.range = bound
        else:
            bit = 1
            self.code -= bound
            self.range -= bound

        model.update(bit)
        self._normalize()

        return bit

    def _normalize(self):
        while self.range < 0x01000000:
            self.code = ((self.code << 8) | self._read_byte()) & 0xFFFFFFFF
            self.range <<= 8

def encode_length_writer(writer, length):
    m = writer.models

    if 2 <= length <= 9:
        writer.write_bit(m.len_first, 0)
        writer.write_bits(length - 2, 3, m.len_low)

    elif 10 <= length <= 17:
        writer.write_bit(m.len_first, 1)
        writer.write_bit(m.len_second, 0)
        writer.write_bits(length - 10, 3, m.len_mid)

    elif 18 <= length <= 273:
        writer.write_bit(m.len_first, 1)
        writer.write_bit(m.len_second, 1)
        writer.write_bits(length - 18, 8, m.len_high)

    else:
        raise ValueError("Invalid match length")


def decode_length_reader2(reader):
    m = reader.models

    first = reader.read_bit(m.len_first)

    if first == 0:
        return reader.read_bits(3, m.len_low) + 2

    second = reader.read_bit(m.len_second)

    if second == 0:
        return reader.read_bits(3, m.len_mid) + 10

    return reader.read_bits(8, m.len_high) + 18


def encode_distance_writer(writer, dist):
    m = writer.models

    if not (1 <= dist <= WINDOW_SIZE):
        raise ValueError("Invalid distance")

    if dist <= 16:
        writer.write_bit(m.dist_first, 0)
        writer.write_bits(dist - 1, 4, m.dist_low)

    elif dist <= 272:
        writer.write_bit(m.dist_first, 1)
        writer.write_bit(m.dist_second, 0)
        writer.write_bits(dist - 17, 8, m.dist_mid)

    else:
        writer.write_bit(m.dist_first, 1)
        writer.write_bit(m.dist_second, 1)
        writer.write_bits(dist - 273, 12, m.dist_high)


def decode_distance_reader2(reader):
    m = reader.models

    first = reader.read_bit(m.dist_first)

    if first == 0:
        return reader.read_bits(4, m.dist_low) + 1

    second = reader.read_bit(m.dist_second)

    if second == 0:
        return reader.read_bits(8, m.dist_mid) + 17

    return reader.read_bits(12, m.dist_high) + 273

def range_encode_bits(bits):
    encoder = RangeEncoder()
    model = BitModel()

    for bit in bits:
        encoder.encode_bit(model, bit)

    return encoder.finish()

def range_decode_bits(encoded_data, bit_count):
    decoder = RangeDecoder(encoded_data)
    model = BitModel()
    bits = []

    for _ in range(bit_count):
        bit = decoder.decode_bit(model)
        bits.append(bit)

    return bits


def to_bits(value, bits):
    return [(value >> (bits - 1 - i)) & 1 for i in range(bits)]


def bits_to_int(bits):
    value = 0
    for b in bits:
        value = (value << 1) | b
    return value


def get_key(data, pos):
    if pos + HASH_LEN > len(data):
        return None
    return bytes(data[pos:pos + HASH_LEN])


def match_length(data, pos1, pos2):
    length = 0

    while (
        length < MAX_LEN
        and pos1 + length < len(data)
        and pos2 + length < len(data)
        and data[pos1 + length] == data[pos2 + length]
    ):
        length += 1

    return length


def add_position(data, pos, table):
    key = get_key(data, pos)

    if key is None:
        return

    table[key].append(pos)

    while table[key] and pos - table[key][0] > WINDOW_SIZE:
        table[key].popleft()


def find_match_fast(data, pos, table):
    key = get_key(data, pos)

    if key is None:
        return 0, 0

    best_len = 0
    best_dist = 0
    checked = 0

    for prev_pos in reversed(table.get(key, [])):
        dist = pos - prev_pos

        if dist <= 0:
            continue

        if dist > WINDOW_SIZE:
            break

        length = match_length(data, prev_pos, pos)

        if length > best_len:
            best_len = length
            best_dist = dist

        checked += 1
        if checked >= MAX_CANDIDATES:
            break

    if best_len >= 2:
        return best_len, best_dist

    return 0, 0


def find_best_rep(data, pos, reps):
    best_len = 0
    best_rep_index = -1

    for i, dist in enumerate(reps):
        if dist <= 0:
            continue

        prev_pos = pos - dist

        if prev_pos < 0:
            continue

        length = match_length(data, prev_pos, pos)

        if length > best_len:
            best_len = length
            best_rep_index = i

    if best_len >= 2:
        return best_rep_index, best_len

    return -1, 0


def move_rep_to_front(reps, index):
    dist = reps[index]

    for i in range(index, 0, -1):
        reps[i] = reps[i - 1]

    reps[0] = dist


def add_new_distance(reps, dist):
    reps[3] = reps[2]
    reps[2] = reps[1]
    reps[1] = reps[0]
    reps[0] = dist


def encode_lz(data):
    if isinstance(data, str):
        data = data.encode("utf-8")

    table = defaultdict(deque)
    packets = []
    pos = 0

    reps = [1, 1, 1, 1]

    while pos < len(data):
        # 1. ShortRep: один байт з rep0
        if pos - reps[0] >= 0 and data[pos] == data[pos - reps[0]]:
            packets.append(ShortRep())
            add_position(data, pos, table)
            pos += 1
            continue

        # 2. LongRep: довший повтор з rep0/rep1/rep2/rep3
        rep_index, rep_len = find_best_rep(data, pos, reps)

        # 3. Звичайний Match: нова distance
        match_len, match_dist = find_match_fast(data, pos, table)

        if rep_len >= 2 and rep_len >= match_len:
            packets.append(LongRep(rep_index, rep_len))
            move_rep_to_front(reps, rep_index)

            for skipped_pos in range(pos, pos + rep_len):
                add_position(data, skipped_pos, table)

            pos += rep_len

        elif match_len >= 2:
            packets.append(Match(match_len, match_dist))
            add_new_distance(reps, match_dist)

            for skipped_pos in range(pos, pos + match_len):
                add_position(data, skipped_pos, table)

            pos += match_len

        else:
            packets.append(Literal(data[pos]))
            add_position(data, pos, table)
            pos += 1

    return packets


def encode_length(length):
    if 2 <= length <= 9:
        return [0] + to_bits(length - 2, 3)

    elif 10 <= length <= 17:
        return [1, 0] + to_bits(length - 10, 3)

    elif 18 <= length <= 273:
        return [1, 1] + to_bits(length - 18, 8)

    else:
        raise ValueError("Invalid match length")


def decode_length(bits, pos):
    if bits[pos] == 0:
        pos += 1
        length = bits_to_int(bits[pos:pos + 3]) + 2
        pos += 3
        return length, pos

    pos += 1

    if bits[pos] == 0:
        pos += 1
        length = bits_to_int(bits[pos:pos + 3]) + 10
        pos += 3
        return length, pos

    pos += 1
    length = bits_to_int(bits[pos:pos + 8]) + 18
    pos += 8
    return length, pos


def encode_distance(dist):
    """
    distance 1..16      → 5 біт
    distance 17..272    → 10 біт
    distance 273..4096  → 14 біт
    """
    if not (1 <= dist <= WINDOW_SIZE):
        raise ValueError("Invalid distance")

    if dist <= 16:
        # 0 + 4 біти
        return [0] + to_bits(dist - 1, 4)

    elif dist <= 272:
        # 10 + 8 біт
        return [1, 0] + to_bits(dist - 17, 8)

    else:
        # 11 + 12 біт
        return [1, 1] + to_bits(dist - 273, 12)

def decode_distance(bits, pos):
    first = bits[pos]
    pos += 1

    if first == 0:
        dist = bits_to_int(bits[pos:pos + 4]) + 1
        pos += 4
        return dist, pos

    second = bits[pos]
    pos += 1

    if second == 0:
        dist = bits_to_int(bits[pos:pos + 8]) + 17
        pos += 8
        return dist, pos

    dist = bits_to_int(bits[pos:pos + 12]) + 273
    pos += 12
    return dist, pos

def packets_to_bits(packets):
    """
    1100 = ShortRep
    1101 = EndMarker
    """
    bits = []

    for p in packets:
        if isinstance(p, Literal):
            bits.append(0)
            bits += to_bits(p.byte, 8)

        elif isinstance(p, Match):
            bits += [1, 0]
            bits += encode_length(p.length)
            bits += encode_distance(p.distance)

        elif isinstance(p, ShortRep):
            bits += [1, 1, 0, 0]

        elif isinstance(p, LongRep):
            bits += [1, 1, 1]
            bits += to_bits(p.rep_index, 2)
            bits += encode_length(p.length)

    # 1101 = END
    bits += [1, 1, 0, 1]

    return bits

def pack_bits(bits):
    out = []
    cur = 0
    count = 0

    for b in bits:
        cur = (cur << 1) | b
        count += 1

        if count == 8:
            out.append(cur)
            cur = 0
            count = 0

    if count > 0:
        cur <<= (8 - count)  #доповнюєнулями справа
        out.append(cur)

    return bytes(out)

def unpack_bits(data):
    bits = []

    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)

    return bits

def decode(bits):
    pos = 0
    output = []
    reps = [1, 1, 1, 1]

    while pos < len(bits):
        first = bits[pos]
        pos += 1

        if first == 0:
            byte = bits_to_int(bits[pos:pos + 8])
            pos += 8
            output.append(byte)

        else:
            second = bits[pos]
            pos += 1

            if second == 0:
                # Match
                length, pos = decode_length(bits, pos)
                dist, pos = decode_distance(bits, pos)

                for _ in range(length):
                    output.append(output[-dist])

                add_new_distance(reps, dist)

            else:
                third = bits[pos]
                pos += 1

                if third == 0:
                    fourth = bits[pos]
                    pos += 1

                    if fourth == 1:
                        break  # EndMarker

                    # ShortRep = rep0, length 1
                    output.append(output[-reps[0]])

                else:
                    # LongRep
                    rep_index = bits_to_int(bits[pos:pos + 2])
                    pos += 2

                    length, pos = decode_length(bits, pos)
                    dist = reps[rep_index]

                    for _ in range(length):
                        output.append(output[-dist])

                    move_rep_to_front(reps, rep_index)

    return bytes(output)

def decode_length_reader(reader):
    first = reader.read_bit()

    if first == 0:
        return reader.read_bits(3) + 2

    second = reader.read_bit()

    if second == 0:
        return reader.read_bits(3) + 10

    return reader.read_bits(8) + 18


def decode_distance_reader(reader):
    first = reader.read_bit()

    if first == 0:
        return reader.read_bits(4) + 1

    second = reader.read_bit()

    if second == 0:
        return reader.read_bits(8) + 17

    return reader.read_bits(12) + 273
class RangeBitReader:
    def __init__(self, data):
        self.decoder = RangeDecoder(data)
        self.model = BitModel()

    def read_bit(self):
        return self.decoder.decode_bit(self.model)

    def read_bits(self, n):
        value = 0
        for _ in range(n):
            value = (value << 1) | self.read_bit()
        return value
def compress(data):
    packets = encode_lz(data)
    writer = RangeBitWriter()
    m = writer.models

    for p in packets:
        if isinstance(p, Literal):
            # 0 + literal byte
            writer.write_bit(m.first, 0)
            writer.write_bits(p.byte, 8, m.literal)

        elif isinstance(p, Match):
            # 10 + length + distance
            writer.write_bit(m.first, 1)
            writer.write_bit(m.second, 0)
            encode_length_writer(writer, p.length)
            encode_distance_writer(writer, p.distance)

        elif isinstance(p, ShortRep):
            # 1100
            writer.write_bit(m.first, 1)
            writer.write_bit(m.second, 1)
            writer.write_bit(m.third, 0)
            writer.write_bit(m.fourth, 0)

        elif isinstance(p, LongRep):
            # 111 + rep_index + length
            writer.write_bit(m.first, 1)
            writer.write_bit(m.second, 1)
            writer.write_bit(m.third, 1)
            writer.write_bits(p.rep_index, 2, m.rep_index)
            encode_length_writer(writer, p.length)

    # EndMarker = 1101
    writer.write_bit(m.first, 1)
    writer.write_bit(m.second, 1)
    writer.write_bit(m.third, 0)
    writer.write_bit(m.fourth, 1)

    return writer.finish()


def decompress(blob):
    reader = RangeBitReader2(blob)
    m = reader.models

    output = []
    reps = [1, 1, 1, 1]

    while True:
        first = reader.read_bit(m.first)

        if first == 0:
            byte = reader.read_bits(8, m.literal)
            output.append(byte)

        else:
            second = reader.read_bit(m.second)

            if second == 0:
                length = decode_length_reader2(reader)
                dist = decode_distance_reader2(reader)

                if dist > len(output):
                    raise ValueError("Invalid distance")

                for _ in range(length):
                    output.append(output[-dist])

                add_new_distance(reps, dist)

            else:
                third = reader.read_bit(m.third)

                if third == 0:
                    fourth = reader.read_bit(m.fourth)

                    if fourth == 1:
                        break  # EndMarker

                    if reps[0] > len(output):
                        raise ValueError("Invalid rep distance")

                    output.append(output[-reps[0]])

                else:
                    rep_index = reader.read_bits(2, m.rep_index)
                    length = decode_length_reader2(reader)
                    dist = reps[rep_index]

                    if dist > len(output):
                        raise ValueError("Invalid rep distance")

                    for _ in range(length):
                        output.append(output[-dist])

                    move_rep_to_front(reps, rep_index)

    return bytes(output)


# ---- тест ----
if __name__ == '__main__':

    data = b"abcabcabcaaaaa"
    packets = encode_lz(data)
    bits = packets_to_bits(packets)

    compressed = range_encode_bits(bits)

    restored_bits = range_decode_bits(compressed, len(bits))
    decoded = decode(restored_bits)

    print(decoded == data)
    data = b"abcabcabcaaaaa"

    compressed = compress(data)
    restored = decompress(compressed)

    print(compressed)
    print(restored)
    print(restored == data)
    text = "привіт привіт привіт"

    compressed = compress(text.encode("utf-8"))
    restored = decompress(compressed).decode("utf-8")

    print(restored)
