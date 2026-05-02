class FenwickTree:
    """Prefix sum tree: query і update за O(log n)"""
    def __init__(self, size):
        self.n = size
        self.tree = [0] * (size + 1)

    def update(self, i, delta=1):
        """Додає delta до позиції i (1-indexed)"""
        while i <= self.n:
            self.tree[i] += delta
            i += i & (-i)

    def query(self, i):
        """Повертає префіксну суму [1..i]"""
        s = 0
        while i > 0:
            s += self.tree[i]
            i -= i & (-i)
        return s

    def find(self, target):
        """Бінарний пошук: перший i такий що query(i) > target — O(log n)"""
        pos = 0
        log = self.n.bit_length()
        for i in range(log, -1, -1):
            npos = pos + (1 << i)
            if npos <= self.n and self.tree[npos] <= target:
                target -= self.tree[npos]
                pos = npos
        return pos  # 0-indexed символ


class ArithmeticAlgorithm:
    def __init__(self, precision=32):
        self.PRECISION = precision
        self.MAX_VALUE = (1 << precision) - 1
        self.ONE_FOURTH = (self.MAX_VALUE + 1) // 4
        self.ONE_HALF = 2 * self.ONE_FOURTH
        self.THREE_FOURTHS = 3 * self.ONE_FOURTH
        self.bit_buffer = 0
        self.bit_count = 0

    def _make_model(self):
        """257 символів (0-255 + EOF=256), кожен з початковою частотою 1"""
        ft = FenwickTree(257)
        for i in range(1, 258):  # 1-indexed
            ft.update(i, 1)
        return ft, 257  # total_freq

    def _output_bit(self, res, bit):
        self.bit_buffer = (self.bit_buffer << 1) | bit
        self.bit_count += 1
        if self.bit_count == 8:
            res.append(self.bit_buffer)
            self.bit_buffer = 0
            self.bit_count = 0

    def _output_bits(self, res, bit, n):
        self._output_bit(res, bit)
        for _ in range(n):
            self._output_bit(res, 1 - bit)

    def compress(self, data: bytes) -> bytes:
        self.bit_buffer = 0
        self.bit_count = 0

        ft, total_freq = self._make_model()
        low, high = 0, self.MAX_VALUE
        bits_to_follow = 0
        res = bytearray()

        for char in list(data) + [256]:
            sym = char + 1  # 1-indexed у Fenwick Tree

            char_low_count = ft.query(sym - 1)      # сума [1..sym-1]
            char_high_count = ft.query(sym)          # сума [1..sym]

            range_width = high - low + 1
            high = low + (range_width * char_high_count) // total_freq - 1
            low = low + (range_width * char_low_count) // total_freq

            while True:
                if high < self.ONE_HALF:
                    self._output_bits(res, 0, bits_to_follow)
                    bits_to_follow = 0
                elif low >= self.ONE_HALF:
                    self._output_bits(res, 1, bits_to_follow)
                    bits_to_follow = 0
                    low -= self.ONE_HALF
                    high -= self.ONE_HALF
                elif low >= self.ONE_FOURTH and high < self.THREE_FOURTHS:
                    bits_to_follow += 1
                    low -= self.ONE_FOURTH
                    high -= self.ONE_FOURTH
                else:
                    break
                low = (low << 1) & self.MAX_VALUE
                high = ((high << 1) | 1) & self.MAX_VALUE

            ft.update(sym, 1)  # O(log 257)
            total_freq += 1

        bits_to_follow += 1
        if low < self.ONE_FOURTH:
            self._output_bits(res, 0, bits_to_follow)
        else:
            self._output_bits(res, 1, bits_to_follow)

        if self.bit_count > 0:
            res.append(self.bit_buffer << (8 - self.bit_count))

        return bytes(res)

    def decompress(self, compressed_data: bytes) -> bytes:
        if not compressed_data:
            return b""

        def get_bits(data):
            for byte in data:
                for i in range(7, -1, -1):
                    yield (byte >> i) & 1

        bit_gen = get_bits(compressed_data)
        ft, total_freq = self._make_model()

        low, high = 0, self.MAX_VALUE
        value = 0
        for _ in range(self.PRECISION):
            value = (value << 1) | next(bit_gen, 0)

        result = bytearray()
        while True:
            range_width = high - low + 1
            scaled_value = ((value - low + 1) * total_freq - 1) // range_width

            # O(log 257) пошук через Fenwick Tree
            char = ft.find(scaled_value)  # 0-indexed

            if char == 256:
                break
            result.append(char)

            sym = char + 1
            char_low_count = ft.query(sym - 1)
            char_high_count = ft.query(sym)

            high = low + (range_width * char_high_count) // total_freq - 1
            low = low + (range_width * char_low_count) // total_freq

            while True:
                if high < self.ONE_HALF:
                    pass
                elif low >= self.ONE_HALF:
                    value -= self.ONE_HALF
                    low -= self.ONE_HALF
                    high -= self.ONE_HALF
                elif low >= self.ONE_FOURTH and high < self.THREE_FOURTHS:
                    value -= self.ONE_FOURTH
                    low -= self.ONE_FOURTH
                    high -= self.ONE_FOURTH
                else:
                    break
                low = (low << 1) & self.MAX_VALUE
                high = ((high << 1) | 1) & self.MAX_VALUE
                value = ((value << 1) | next(bit_gen, 0)) & self.MAX_VALUE

            ft.update(sym, 1)  # O(log 257)
            total_freq += 1

        return bytes(result)


def arithmetic_compress(data):
    return ArithmeticAlgorithm().compress(data)
def arithmetic_decompress(data):
    return ArithmeticAlgorithm().decompress(data)

