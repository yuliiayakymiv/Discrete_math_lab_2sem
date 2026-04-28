import struct

class SimpleLZMA:
    def __init__(self):
        self.PROB_BITS = 11
        self.PROB_TOTAL = 1 << self.PROB_BITS  # 2048
        self.MOVE_BITS = 5
        self.NUM_STATES = 12

    def _update_prob(self, prob, bit):
        if bit == 0:
            return prob + ((self.PROB_TOTAL - prob) >> self.MOVE_BITS)
        else:
            return prob - (prob >> self.MOVE_BITS)

    def compress(self, data):
        if not data: return b""

        probs = [self.PROB_TOTAL // 2] * self.NUM_STATES
        state = 0
        output = bytearray()

        range_low = 0
        range_width = 0xFFFFFFFF
        pos = 0

        while pos < len(data):
            dist, length = self._find_match(data, pos)
            prob_idx = state

            if length >= 3:
                # Кодування '1' (Match)
                bit = 1
                bound = (range_width >> self.PROB_BITS) * probs[prob_idx]
                range_low += bound
                range_width -= bound
                probs[prob_idx] = self._update_prob(probs[prob_idx], bit)

                # Нормалізація перед записом метаданих
                range_low, range_width = self._normalize(range_low, range_width, output)

                # Записування Match-дані
                output.append(0xFF) # Маркер Match
                output.extend(struct.pack(">HH", dist, length))

                pos += length
                state = (state // 2) + 6 # Перехід стану (Марков)
            else:
                # Кодуємо '0' (Literal)
                bit = 0
                bound = (range_width >> self.PROB_BITS) * probs[prob_idx]
                range_width = bound
                probs[prob_idx] = self._update_prob(probs[prob_idx], bit)

                range_low, range_width = self._normalize(range_low, range_width, output)

                output.append(data[pos])
                pos += 1
                state = state // 2

        # Фіналізація Range Coder
        for _ in range(4):
            output.append((range_low >> 24) & 0xFF)
            range_low = (range_low << 8) & 0xFFFFFFFF

        return bytes(output)

    def decompress(self, compressed):
        if not compressed: return b""

        probs = [self.PROB_TOTAL // 2] * self.NUM_STATES
        state = 0
        data = bytearray()

        # Ініціалізація Range Decoder
        range_low = 0
        range_width = 0xFFFFFFFF
        # Читання перших 4 байтів для ініціалізації code
        code = 0
        for i in range(4):
            code = (code << 8) | compressed[i]

        ptr = 4
        while ptr < len(compressed) - 4:
            prob_idx = state
            prob = probs[prob_idx]
            bound = (range_width >> self.PROB_BITS) * prob

            if code >= bound: # Match (1)
                bit = 1
                code -= bound
                range_width -= bound
                probs[prob_idx] = self._update_prob(probs[prob_idx], bit)

                # Нормалізація
                while range_width < (1 << 24) and ptr < len(compressed):
                    code = ((code << 8) | compressed[ptr + 5]) & 0xFFFFFFFF
                    range_width = (range_width << 8) & 0xFFFFFFFF
                    ptr += 1

                # Зчитування даних матчу (ми додали маркер 0xFF перед ними)
                if ptr < len(compressed) and compressed[ptr] == 0xFF:
                    ptr += 1
                    dist, length = struct.unpack(">HH", compressed[ptr:ptr+4])
                    ptr += 4
                    for _ in range(length):
                        data.append(data[len(data) - dist])
                    state = (state // 2) + 6
                else: break
            else: # Literal (0)
                bit = 0
                range_width = bound
                probs[prob_idx] = self._update_prob(probs[prob_idx], bit)

                # Нормалізація
                while range_width < (1 << 24) and ptr < len(compressed):
                    code = ((code << 8) | compressed[ptr + 1]) & 0xFFFFFFFF
                    range_width = (range_width << 8) & 0xFFFFFFFF
                    ptr += 1

                if ptr < len(compressed):
                    data.append(compressed[ptr])
                    ptr += 1
                    state = state // 2
                else: break
        return bytes(data)

    def _find_match(self, data, pos):
        best_len, best_dist = 0, 0
        search_limit = max(0, pos - 4096)
        for j in range(search_limit, pos):
            l = 0
            while pos + l < len(data) and data[j+l] == data[pos+l] and l < 255:
                l += 1
            if l > best_len:
                best_len, best_dist = l, pos - j
        return best_dist, best_len

    def _normalize(self, low, width, out):
        while width < (1 << 24):
            out.append((low >> 24) & 0xFF)
            low = (low << 8) & 0xFFFFFFFF
            width = (width << 8) & 0xFFFFFFFF
        return low, width

def run_lzma_algorithm(data, mode='compress'):
    lzma = SimpleLZMA()
    if mode == 'compress':
        if isinstance(data, str):
            data = data.encode()
        return lzma.compress(data)
    else:
        return lzma.decompress(data)
