import struct
import argparse
from collections import Counter
import heapq
import os
import time


class BitWriter:
    def __init__(self, file):
        self.file = file
        self.buffer = 0       # bit accumulator
        self.bits_count = 0   # how many bits are in the buffer

    def write_bit(self, bit):
        # shift left to make room, | inserts the new bit on the right
        self.buffer = (self.buffer << 1) | (bit & 1)
        self.bits_count += 1
        if self.bits_count == 8:
            # buffer full — write byte to file
            self.file.write(struct.pack('B', self.buffer))
            self.buffer = 0
            self.bits_count = 0

    def write_bits(self, value, length):
        # write bits left to right (most significant first)
        for i in range(length - 1, -1, -1):
            self.write_bit((value >> i) & 1)

    def flush(self):
        # pad the last incomplete byte with zeros on the right
        if self.bits_count > 0:
            self.buffer <<= (8 - self.bits_count)
            self.file.write(struct.pack('B', self.buffer))
            self.buffer = 0
            self.bits_count = 0


class BitReader:
    def __init__(self, file):
        self.file = file
        self.buffer = 0
        self.bits_count = 0

    def read_bit(self):
        if self.bits_count == 0:
            # buffer exhausted — load next byte
            byte = self.file.read(1)
            if not byte:
                return None  # end of file
            self.buffer = byte[0]
            self.bits_count = 8
        # shift right puts the target bit in last position, & 1 masks the rest
        bit = (self.buffer >> (self.bits_count - 1)) & 1
        self.bits_count -= 1
        return bit

    def read_bits(self, length):
        # assemble length bits into a single number
        value = 0
        for _ in range(length):
            bit = self.read_bit()
            if bit is None:
                break
            value = (value << 1) | bit
        return value


class HuffMan:
    def build_tree(self, data):
        freq = Counter(str(x) for x in data)
        if not freq:
            return None

        # edge case: only one unique symbol — heapq loop would never run
        if len(freq) == 1:
            return {next(iter(freq)): '0'}

        # repeatedly merge the two lightest nodes
        heap = [[weight, [symbol, '']] for symbol, weight in freq.items()]
        heapq.heapify(heap)
        while len(heap) > 1:
            low  = heapq.heappop(heap)
            high = heapq.heappop(heap)
            for pair in low[1:]:
                pair[1] = '0' + pair[1]  # left branch gets 0
            for pair in high[1:]:
                pair[1] = '1' + pair[1]  # right branch gets 1
            heapq.heappush(heap, [low[0] + high[0]] + low[1:] + high[1:])
        return dict(heap[0][1:])  # { symbol: bit_code }


class LZ77:
    def __init__(self):
        self.window_size = 32768  # search window size

    def compress(self, data):
        i = 0
        output = []
        while i < len(data):
            match_len = 0
            match_dist = 0
            start = max(0, i - self.window_size)

            # find the longest match in the window
            for j in range(start, i):
                length = 0
                while (i + length < len(data) and
                       data[j + length] == data[i + length] and
                       length < 255):
                    length += 1
                if length > match_len:
                    match_len = length
                    match_dist = i - j

            if match_len >= 3:
                # worth storing as a back-reference (distance, length)
                output.append((match_dist, match_len))
                i += match_len
            else:
                # not worth it — store as literal
                output.append(data[i])
                i += 1
        return output


def deflate_compress(input_file_path: str, output_file_path: str):
    with open(input_file_path, 'rb') as f:
        data = f.read()

    lz77_output = LZ77().compress(data)
    codes = HuffMan().build_tree(lz77_output)  # { symbol: bit_code }

    with open(output_file_path, 'wb') as out_f:

        #HEADER (direct writes only, no BitWriter)
        # Rule: never mix BitWriter and direct f.write() —
        # BitWriter buffers bits internally, so direct writes in between
        # would land in the file out of order.

        out_f.write(struct.pack('<I', len(codes)))       # number of unique symbols
        out_f.write(struct.pack('<Q', len(lz77_output))) # number of symbols in stream
                                                         # (guards against flush padding bits)
        for symbol_str, code_str in codes.items():
            sym_bytes  = symbol_str.encode('latin-1')
            code_bytes = code_str.encode('latin-1')  # code stored as ASCII '0'/'1'
                                                     # (preserves leading zeros)
            out_f.write(struct.pack('B', len(sym_bytes)))
            out_f.write(sym_bytes)
            out_f.write(struct.pack('B', len(code_bytes)))
            out_f.write(code_bytes)

        # BIT STREAM (BitWriter only)
        bw = BitWriter(out_f)
        for item in lz77_output:
            for bit_ch in codes[str(item)]:
                bw.write_bit(int(bit_ch))
        bw.flush()  # write the last incomplete byte


def _parse_symbol(symbol_str: str):
    # "(13, 11)" → tuple,  "97" → int
    s = symbol_str.strip()
    if s.startswith('(') and s.endswith(')'):
        a, b = s[1:-1].split(',')
        return (int(a.strip()), int(b.strip()))
    return int(s)


def deflate_decompress(input_file_path: str, output_file_path: str):
    with open(input_file_path, 'rb') as f:

        # HEADER (direct reads, before BitReader)
        header = f.read(4)
        if not header:
            return
        num_codes   = struct.unpack('<I', header)[0]
        num_symbols = struct.unpack('<Q', f.read(8))[0]

        # rebuild lookup table: { bit_code: symbol } (inverted vs compress)
        reverse_codes = {}
        for _ in range(num_codes):
            sym_str  = f.read(struct.unpack('B', f.read(1))[0]).decode('latin-1')
            code_str = f.read(struct.unpack('B', f.read(1))[0]).decode('latin-1')
            reverse_codes[code_str] = sym_str

        # ── BIT STREAM ──
        br = BitReader(f)
        out_data = []
        current_bits = ""
        decoded_count = 0

        while decoded_count < num_symbols:  # stop exactly at num_symbols, skip padding
            bit = br.read_bit()
            if bit is None:
                break
            current_bits += str(bit)

            if current_bits in reverse_codes:
                item = _parse_symbol(reverse_codes[current_bits])
                decoded_count += 1

                if isinstance(item, tuple):
                    # LZ77 back-reference — copy from already decoded data
                    dist, length = item
                    start_pos = len(out_data) - dist
                    for i in range(length):
                        out_data.append(out_data[start_pos + i])
                else:
                    # literal — append byte directly
                    out_data.append(item)

                current_bits = ""

    with open(output_file_path, 'wb') as f_out:
        f_out.write(bytearray(out_data))  # list of ints → bytes → file


def test_function(input_name, output_name):
    start = time.time()
    deflate_compress(input_name, output_name)
    end_time = time.time()
    time_ = round(end_time - start, 2)
    size = os.path.getsize(output_name)/1000
    return time_, size


import zlib
import bz2
import lzma

def test_other(filename):
    with open(filename, "rb") as f:
        data = f.read()

    results = {}

    for name, func in {
        "zlib": zlib.compress,
        "bz2": bz2.compress,
        "lzma": lzma.compress,
    }.items():

        start = time.perf_counter()
        compressed = func(data)
        end = time.perf_counter()

        results[name] = {
            "time": end - start,
            "size": len(compressed)
        }

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Custom Deflate Archiver")
    parser.add_argument("input",  help="Path to input file")
    parser.add_argument("output", help="Path to output file")
    parser.add_argument("--mode", choices=['c', 'd'], default='c',
                        help="c - compress, d - decompress")
    args = parser.parse_args()

    if args.mode == 'c':
        deflate_compress(args.input, args.output)
        print(f"Compressed: {args.input} → {args.output}")
    else:
        deflate_decompress(args.input, args.output)
        print(f"Decompressed: {args.input} → {args.output}")
