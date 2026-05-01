import struct

class RangeCoder:
    def __init__(self, data=None):
        self.low = 0
        self.range = 0xFFFFFFFF
        self.output = bytearray()
        self.code = 0
        if data:
            # Починаємо читати дані після 4 байтів розміру
            self.data = data
            for i in range(5):
                self.code = (self.code << 8) | (self.data[i] if i < len(self.data) else 0)
            self.ptr = 5
        else:
            self.data = None
            self.ptr = 0

    def encode_bit(self, prob, bit):
        bound = (self.range >> 11) * prob
        if bit == 0:
            self.range = bound
            prob += (2048 - prob) >> 5
        else:
            self.low += bound
            self.range -= bound
            prob -= prob >> 5

        while self.range < 0x01000000:
            self.output.append((self.low >> 24) & 0xFF)
            self.low = (self.low << 8) & 0xFFFFFFFF
            self.range = (self.range << 8) & 0xFFFFFFFF
        return prob

    def decode_bit(self, prob):
        bound = (self.range >> 11) * prob
        if self.code < bound:
            bit = 0
            self.range = bound
            prob += (2048 - prob) >> 5
        else:
            bit = 1
            self.code -= bound
            self.range -= bound
            prob -= prob >> 5

        while self.range < 0x01000000:
            new_byte = self.data[self.ptr] if self.ptr < len(self.data) else 0
            self.code = ((self.code << 8) | new_byte) & 0xFFFFFFFF
            self.range = (self.range << 8) & 0xFFFFFFFF
            self.ptr += 1
        return bit, prob

    def finalize(self):
        for _ in range(5):
            self.output.append((self.low >> 24) & 0xFF)
            self.low = (self.low << 8) & 0xFFFFFFFF

class SimpleLZMA:
    def __init__(self):
        self.INIT_PROB = 1024
        # Окремі ймовірності для всього
        self.is_match_probs = [self.INIT_PROB] * 12
        self.lit_probs = [self.INIT_PROB] * (12 * 256)
        self.len_probs = [self.INIT_PROB] * 256
        self.dist_probs = [self.INIT_PROB] * 4096 # Для вікна 4кб

    def compress(self, data):
        if not data: return b""
        rc = RangeCoder()
        state = 0
        pos = 0

        # 1. Записуємо розмір оригіналу (для надійної декомпресії)
        header = struct.pack("<I", len(data))

        while pos < len(data):
            dist, length = self._find_match(data, pos)

            if length >= 3:
                # Кодуємо '1' (Match)
                self.is_match_probs[state] = rc.encode_bit(self.is_match_probs[state], 1)

                # Кодуємо довжину (8 біт)
                for i in range(8):
                    bit = (length >> i) & 1
                    self.len_probs[i] = rc.encode_bit(self.len_probs[i], bit)

                # Кодуємо дистанцію (12 біт для вікна 4096)
                for i in range(12):
                    bit = (dist >> i) & 1
                    self.dist_probs[i] = rc.encode_bit(self.dist_probs[i], bit)

                pos += length
                state = (state // 2) + 6
            else:
                # Кодуємо '0' (Literal)
                self.is_match_probs[state] = rc.encode_bit(self.is_match_probs[state], 0)

                byte = data[pos]
                # for i in range(7, -1, -1):
                #     bit = (byte >> i) & 1
                #     idx = (state * 256) + byte # Спрощене контекстне моделювання
                #     self.lit_probs[idx % (12*256)] = rc.encode_bit(self.lit_probs[idx % (12*256)], bit)
                # Замість складної формули, використовуй тільки позицію біта
                for i in range(7, -1, -1):
                    bit = (byte >> i) & 1
                    prob_idx = i  # Спрощуємо до 8 ймовірностей (по одній на кожен біт байта)
                    self.lit_probs[prob_idx] = rc.encode_bit(self.lit_probs[prob_idx], bit)

                pos += 1
                state = state // 2 if state < 6 else 3

        rc.finalize()
        return header + bytes(rc.output)

    def decompress(self, compressed):
        if len(compressed) < 4: return b""

        # Читаємо розмір з заголовка
        orig_size = struct.unpack("<I", compressed[:4])[0]
        rc = RangeCoder(compressed[4:])

        data = bytearray()
        state = 0

        while len(data) < orig_size:
            bit, self.is_match_probs[state] = rc.decode_bit(self.is_match_probs[state])

            if bit == 1: # Match
                length = 0
                for i in range(8):
                    b, self.len_probs[i] = rc.decode_bit(self.len_probs[i])
                    length |= (b << i)

                dist = 0
                for i in range(12):
                    b, self.dist_probs[i] = rc.decode_bit(self.dist_probs[i])
                    dist |= (b << i)

                for _ in range(length):
                    if len(data) - dist >= 0:
                        data.append(data[len(data) - dist])
                state = (state // 2) + 6
            else: # Literal
                byte = 0
                # for i in range(7, -1, -1):
                #     # Використовуємо ту саму логіку індексу, що і при компресії
                #     idx = (state * 256) # спрощено
                #     b, self.lit_probs[idx % (12*256)] = rc.decode_bit(self.lit_probs[idx % (12*256)])
                #     byte |= (b << i)
                # Має бути ідентично компресору!
                for i in range(7, -1, -1):
                    prob_idx = i
                    b, self.lit_probs[prob_idx] = rc.decode_bit(self.lit_probs[prob_idx])
                    byte |= (b << i)
                data.append(byte)
                state = state // 2 if state < 6 else 3

        return bytes(data)

    def _find_match(self, data, pos):
        best_len, best_dist = 0, 0
        # Обмеження вікна 4095 для 12-бітного кодування дистанції
        search_limit = max(0, pos - 4095)
        for j in range(search_limit, pos):
            l = 0
            while pos + l < len(data) and data[j+l] == data[pos+l] and l < 255:
                l += 1
            if l > best_len:
                best_len, best_dist = l, pos - j
        return best_dist, best_len

def run_lzma_algorithm(data, mode='compress'):
    codec = SimpleLZMA()
    if mode == 'compress':
        return codec.compress(data)
    return codec.decompress(data)
