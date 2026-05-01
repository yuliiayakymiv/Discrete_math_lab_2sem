"""
Deflate algorithm implementation: LZ77 + Huffman coding
Compression: deflate_compress(input, output)
Decompression: deflate_decompress(input, output)
"""
import os
import argparse
import tempfile

class BitWriter:
    """Writes bits to a byte buffer (LSB-first, as in DEFLATE)."""

    def __init__(self):
        self.bytes_out = bytearray()
        self.current_byte = 0
        self.bits_in_byte = 0  # number of bits already written into currennt byte

    def write_bit(self, bit):
        """mimimi"""
        if bit:
            self.current_byte |= (1 << self.bits_in_byte)
        self.bits_in_byte += 1
        if self.bits_in_byte == 8:
            self.bytes_out.append(self.current_byte)
            self.current_byte = 0
            self.bits_in_byte = 0

    def write_bits(self, value, num_bits, msb_first=False):
        """Write num_bits bits from value.
        msb_first=True  -> MSB first (for Huffman codes, prefix-free)
        msb_first=False -> LSB first (for extra bits, sizes, etc.)
        """
        if msb_first:
            for i in range(num_bits - 1, -1, -1):
                self.write_bit((value >> i) & 1)
        else:
            for i in range(num_bits):
                self.write_bit((value >> i) & 1)

    def flush(self):
        """Write the last incomplete byte (pad with zeros)."""
        if self.bits_in_byte > 0:
            self.bytes_out.append(self.current_byte)
            self.current_byte = 0
            self.bits_in_byte = 0

    def get_bytes(self):
        """lalala"""
        self.flush()
        return bytes(self.bytes_out)


class BitReader:
    """Reads bits from a byte array (LSB-first)."""

    def __init__(self, data):
        self.data = data
        self.pos = 0       # position in the byte array
        self.bit_pos = 0   # current bit within the current byte (0..7)

    def read_bit(self):
        """trulala"""
        if self.pos >= len(self.data):
            raise EOFError("End of data while reading a bit")
        bit = (self.data[self.pos] >> self.bit_pos) & 1
        self.bit_pos += 1
        if self.bit_pos == 8:
            self.bit_pos = 0
            self.pos += 1
        return bit

    def read_bits(self, num_bits, msb_first=False):
        """Read num_bits bits.
        msb_first=False -> LSB first (for extra bits, default)
        msb_first=True  -> MSB first (for Huffman codes)
        """
        if msb_first:
            value = 0
            for _ in range(num_bits):
                value = (value << 1) | self.read_bit()
            return value
        else:
            value = 0
            for i in range(num_bits):
                value |= self.read_bit() << i
            return value

    def align_to_byte(self):
        """Align to the next byte boundary (skip remaining bits in current byte)."""
        if self.bit_pos != 0:
            self.bit_pos = 0
            self.pos += 1

    def read_byte(self):
        """omg"""
        self.align_to_byte()
        if self.pos >= len(self.data):
            raise EOFError("End of data while reading a byte")
        b = self.data[self.pos]
        self.pos += 1
        return b

    def read_uint16_le(self):
        """hohoho"""
        lo = self.read_byte()
        hi = self.read_byte()
        return lo | (hi << 8)


WINDOW_SIZE = 32768   # 32 KB sliding window
MAX_MATCH_LEN = 258   # maximum match length (per DEFLATE spec)
MIN_MATCH_LEN = 3     # minimum match length


class LZ77Token:
    """LZ77 token: either a literal (byte) or a back-reference (distance, length)."""

    def __init__(self, literal=None, distance=None, length=None):
        self.literal = literal    # int 0-255 for literals
        self.distance = distance  # int 1-32768 for back-references
        self.length = length      # int 3-258 for back-references

    def is_literal(self):
        """sol-la-ti-do"""
        return self.literal is not None

    def __repr__(self):
        if self.is_literal():
            return f"Lit({self.literal})"
        return f"Ref(dist={self.distance}, len={self.length})"


class LZ77:
    """LZ77 compressor with a sliding window."""

    def compress(self, data):
        """Compress a byte array. Returns a list of LZ77Token."""
        tokens = []
        pos = 0
        n = len(data)

        while pos < n:
            best_length = 0
            best_distance = 0

            window_start = max(0, pos - WINDOW_SIZE)  # start of the search window

            if pos + MIN_MATCH_LEN <= n:
                candidate = pos - 1
                while candidate >= window_start:
                    match_len = 0
                    while (match_len < MAX_MATCH_LEN
                           and pos + match_len < n
                           and data[candidate + match_len] == data[pos + match_len]):
                        match_len += 1
                        # overlapping matches are valid in LZ77
                        if candidate + match_len >= pos:
                            pass

                    if match_len > best_length:
                        best_length = match_len
                        best_distance = pos - candidate

                    if best_length == MAX_MATCH_LEN:  # stop early when(if) max match is found
                        break

                    candidate -= 1

            if best_length >= MIN_MATCH_LEN:
                tokens.append(LZ77Token(distance=best_distance, length=best_length))
                pos += best_length
            else:
                tokens.append(LZ77Token(literal=data[pos]))
                pos += 1

        return tokens

    def decompress(self, tokens):
        """Decompress a list of LZ77Token into bytes."""
        output = bytearray()
        for token in tokens:
            if token.is_literal():
                output.append(token.literal)
            else:
                start = len(output) - token.distance
                for i in range(token.length):
                    output.append(output[start + i])
        return bytes(output)


class HuffmanNode:
    """Nodes."""
    def __init__(self, symbol=None, freq=0, left=None, right=None):
        self.symbol = symbol  # None for internal nodes
        self.freq = freq
        self.left = left
        self.right = right

    def is_leaf(self):
        """lalala"""
        return self.symbol is not None


class HuffMan:
    """Canonical Huffman tree construction and encoding/decoding (as used in DEFLATE)."""

    def build_tree(self, frequencies):
        """Build a Huffman tree from a frequency dict {symbol: count}.
        Returns the root node.
        """
        if len(frequencies) == 1:
            # wrap a single unique symbol so the leaf gets depth 1 so the code length 1
            sym = list(frequencies.keys())[0]
            leaf = HuffmanNode(symbol=sym, freq=frequencies[sym])
            dummy = HuffmanNode(symbol=sym, freq=0)
            root = HuffmanNode(freq=frequencies[sym], left=leaf, right=dummy)
            return root

        nodes = []
        for sym, freq in frequencies.items():
            nodes.append(HuffmanNode(symbol=sym, freq=freq))

        while len(nodes) > 1:  # greedy merge is combining two lowest-frequency nodes
            nodes.sort(key=lambda x: (x.freq, x.symbol if x.symbol is not None else -1))
            left = nodes.pop(0)
            right = nodes.pop(0)
            parent = HuffmanNode(
                freq=left.freq + right.freq,
                left=left,
                right=right
            )
            nodes.append(parent)

        return nodes[0]

    def get_code_lengths(self, root):
        """Compute code lengths for each symbol via tree traversal.
        Returns dict {symbol: length}.
        """
        lengths = {}

        def traverse(node, depth):
            if node is None:
                return
            if node.is_leaf():
                lengths[node.symbol] = max(depth, 1)
                return
            traverse(node.left, depth + 1)
            traverse(node.right, depth + 1)

        traverse(root, 0)
        return lengths

    def build_canonical_codes(self, code_lengths):
        """Build canonical Huffman codes from code lengths.
        code_lengths: dict {symbol: length}
        Returns dict {symbol: (code_int, length)}.
        """
        if not code_lengths:
            return {}

        max_len = 15  # DEFLATE maximum code length
        for sym in code_lengths:
            if code_lengths[sym] > max_len:
                code_lengths[sym] = max_len

        max_length = max(code_lengths.values())
        symbols_by_length = {}
        for sym, length in code_lengths.items():
            if length not in symbols_by_length:
                symbols_by_length[length] = []
            symbols_by_length[length].append(sym)
        for length in symbols_by_length:
            symbols_by_length[length].sort()

        codes = {}
        code = 0
        for length in range(1, max_length + 1):
            for sym in symbols_by_length.get(length, []):
                codes[sym] = (code, length)
                code += 1
            code <<= 1  # shift up for the next level

        return codes

    def build_decode_table(self, codes):
        """Build a decode lookup table: (code_int, length) -> symbol."""
        decode_table = {}
        for sym, (code, length) in codes.items():
            decode_table[(code, length)] = sym
        return decode_table

    def encode_frequencies(self, data):
        """Full pipeline: count frequencies -> build tree -> canonical codes.
        data: list of int symbols.
        Returns (codes dict, decode_table dict).
        """
        frequencies = {}
        for sym in data:
            frequencies[sym] = frequencies.get(sym, 0) + 1

        root = self.build_tree(dict(frequencies))
        lengths = self.get_code_lengths(root)
        codes = self.build_canonical_codes(lengths)
        decode_table = self.build_decode_table(codes)
        return codes, decode_table


# DEFLATE literal/length symbol alphabet:
#   0-255  -> literal bytes
#   256    -> end-of-block marker
#   257-285 -> length codes (lengths 3-258)

LENGTH_CODE_TABLE = [
    # (min_len, max_len, base_code, extra_bits)
    (3, 3, 257, 0), (4, 4, 258, 0), (5, 5, 259, 0), (6, 6, 260, 0),
    (7, 7, 261, 0), (8, 8, 262, 0), (9, 9, 263, 0), (10, 10, 264, 0),
    (11, 12, 265, 1), (13, 14, 266, 1), (15, 16, 267, 1), (17, 18, 268, 1),
    (19, 22, 269, 2), (23, 26, 270, 2), (27, 30, 271, 2), (31, 34, 272, 2),
    (35, 42, 273, 3), (43, 50, 274, 3), (51, 58, 275, 3), (59, 66, 276, 3),
    (67, 82, 277, 4), (83, 98, 278, 4), (99, 114, 279, 4), (115, 130, 280, 4),
    (131, 162, 281, 5), (163, 194, 282, 5), (195, 226, 283, 5), (227, 257, 284, 5),
    (258, 258, 285, 0),
]

DISTANCE_CODE_TABLE = [
    # (min_dist, max_dist, code, extra_bits)
    (1, 1, 0, 0), (2, 2, 1, 0), (3, 3, 2, 0), (4, 4, 3, 0),
    (5, 6, 4, 1), (7, 8, 5, 1), (9, 12, 6, 2), (13, 16, 7, 2),
    (17, 24, 8, 3), (25, 32, 9, 3), (33, 48, 10, 4), (49, 64, 11, 4),
    (65, 96, 12, 5), (97, 128, 13, 5), (129, 192, 14, 6), (193, 256, 15, 6),
    (257, 384, 16, 7), (385, 512, 17, 7), (513, 768, 18, 8), (769, 1024, 19, 8),
    (1025, 1536, 20, 9), (1537, 2048, 21, 9), (2049, 3072, 22, 10), (3073, 4096, 23, 10),
    (4097, 6144, 24, 11), (6145, 8192, 25, 11), (8193, 12288, 26, 12), (12289, 16384, 27, 12),
    (16385, 24576, 28, 13), (24577, 32768, 29, 13),
]


def get_length_code(length):
    """Return (code, extra_bits_count, extra_bits_value) for a match length."""
    for (min_l, max_l, code, extra) in LENGTH_CODE_TABLE:
        if min_l <= length <= max_l:
            return code, extra, length - min_l
    raise ValueError(f"Unknown length: {length}")


def get_distance_code(distance):
    """Return (code, extra_bits_count, extra_bits_value) for a back-reference distance."""
    for (min_d, max_d, code, extra) in DISTANCE_CODE_TABLE:
        if min_d <= distance <= max_d:
            return code, extra, distance - min_d
    raise ValueError(f"Unknown distance: {distance}")


def decode_length(code, extra_val):
    """Reconstruct match length from a length code and extra bits."""
    for (min_l, max_l, c, extra) in LENGTH_CODE_TABLE:
        if c == code:
            return min_l + extra_val
    raise ValueError(f"Unknown length code: {code}")


def decode_distance(code, extra_val):
    """Reconstruct distance from a distance code and extra bits."""
    for (min_d, max_d, c, extra) in DISTANCE_CODE_TABLE:
        if c == code:
            return min_d + extra_val
    raise ValueError(f"Unknown distance code: {code}")


def write_huffman_table(writer, codes, max_symbol):
    """Serialise a Huffman table into the bit stream.
    Writes code lengths for symbols 0..max_symbol (inclusive).
    Each length is stored as 4 bits (0 means symbol absent). LSB-first.
    """
    writer.write_bits(max_symbol, 16)
    for sym in range(max_symbol + 1):
        if sym in codes:
            length = codes[sym][1]
        else:
            length = 0
        writer.write_bits(length, 4)


def read_huffman_table(reader):
    """Deserialise a Huffman table from the bit stream.
    Returns decode_table: (code_int, length) -> symbol.
    """
    max_symbol = reader.read_bits(16)
    code_lengths = {}
    for sym in range(max_symbol + 1):
        length = reader.read_bits(4)
        if length > 0:
            code_lengths[sym] = length

    huff = HuffMan()
    codes = huff.build_canonical_codes(code_lengths)
    return huff.build_decode_table(codes)


def tokens_to_litlen_symbols(tokens):
    """Convert LZ77 tokens into a literal/length symbol stream (0-285) and distance info.
    Returns (litlen_symbols list, distance_codes list).
    litlen_symbols: int 0-285 (256 = end-of-block)
    distance_codes: list of (dist_code, dextra_n, dextra_v, lextra_n, lextra_v)
    """
    litlen_symbols = []
    distance_codes = []

    for token in tokens:
        if token.is_literal():
            litlen_symbols.append(token.literal)
        else:
            lcode, lextra_n, lextra_v = get_length_code(token.length)
            dcode, dextra_n, dextra_v = get_distance_code(token.distance)
            litlen_symbols.append(lcode)
            distance_codes.append((dcode, dextra_n, dextra_v, lextra_n, lextra_v))

    litlen_symbols.append(256)  # end-of-block marker
    return litlen_symbols, distance_codes


def deflate_compress(input_file_path: str, output_file_path: str):
    """Compress a file using Deflate (LZ77 + dynamic Huffman).
    Output .deflate format (custom, not zlib/gzip):
      4 bytes: magic number "MEOW"
      4 bytes: original data size (uint32 LE)
      rest:    bit stream with compressed blocks
    """
    
    with open(input_file_path, "rb") as f:
        data = f.read()

    original_size = len(data)



    lz = LZ77()
    tokens = lz.compress(data)


    litlen_symbols, distance_codes = tokens_to_litlen_symbols(tokens)


    huff = HuffMan()

    ll_frequencies = {}
    for sym in litlen_symbols:
        ll_frequencies[sym] = ll_frequencies.get(sym, 0) + 1
    ll_root = huff.build_tree(dict(ll_frequencies))
    ll_lengths = huff.get_code_lengths(ll_root)
    ll_codes = huff.build_canonical_codes(ll_lengths)

    dist_frequencies = {}
    for (dcode, _, _, _, _) in distance_codes:
        dist_frequencies[dcode] = dist_frequencies.get(dcode, 0) + 1
    if dist_frequencies:
        dist_root = huff.build_tree(dict(dist_frequencies))
        dist_lengths = huff.get_code_lengths(dist_root)
        dist_codes = huff.build_canonical_codes(dist_lengths)
    else:
        dist_codes = {}


    writer = BitWriter()

    writer.write_bit(1)          # BFINAL = 1 (last block)
    writer.write_bits(2, 2)      # BTYPE  = 10 (dynamic Huffman)

    ll_max_sym = max(ll_codes.keys()) if ll_codes else 256
    write_huffman_table(writer, ll_codes, ll_max_sym)

    dist_max_sym = max(dist_codes.keys()) if dist_codes else 0
    write_huffman_table(writer, dist_codes, dist_max_sym)

    dist_iter = iter(distance_codes)
    for sym in litlen_symbols:
        if sym not in ll_codes:
            raise ValueError(f"Symbol {sym} missing from Huffman table!")
        code_val, code_len = ll_codes[sym]
        writer.write_bits(code_val, code_len, msb_first=True)  # Huffman codes is MSB-first

        if 257 <= sym <= 285:  # length code: write extra bits + distance
            dcode, dextra_n, dextra_v, lextra_n, lextra_v = next(dist_iter)
            if lextra_n > 0:
                writer.write_bits(lextra_v, lextra_n)          # length extra bits, LSB-first
            if dcode in dist_codes:
                dcode_val, dcode_len = dist_codes[dcode]
                writer.write_bits(dcode_val, dcode_len, msb_first=True)  # distance Huffman code
            else:
                raise ValueError(f"Distance code {dcode} missing from table!")
            if dextra_n > 0:
                writer.write_bits(dextra_v, dextra_n)          # distance extra bits, LSB-first

    compressed_data = writer.get_bytes()
    with open(output_file_path, "wb") as f:
        f.write(b"MEOW")
        f.write(original_size.to_bytes(4, "little"))   # original size header
        f.write(compressed_data)

    compressed_size = os.path.getsize(output_file_path)
    ratio = compressed_size / original_size * 100 if original_size > 0 else 100



def deflate_decompress(input_file_path: str, output_file_path: str):
    """Decompress a .deflate file."""

    with open(input_file_path, "rb") as f:
        raw = f.read()

    if len(raw) < 8:
        raise ValueError("File too small — does not look like a .deflate file")

    if raw[0:4] != b"MEOW":
        raise ValueError(f"Invalid magic number: {raw[0:4]}")

    original_size = int.from_bytes(raw[4:8], "little")


    reader = BitReader(raw[8:])

    bfinal = reader.read_bit()
    btype = reader.read_bits(2)
    if btype != 2:
        raise ValueError(f"Unsupported BTYPE: {btype}")


    ll_decode = read_huffman_table(reader)
    dist_decode = read_huffman_table(reader)


    output = bytearray()

    def read_huffman_symbol(decode_table):
        """Decode one symbol using MSB-first canonical Huffman."""
        code = 0
        length = 0
        while True:
            code = (code << 1) | reader.read_bit()
            length += 1
            if (code, length) in decode_table:
                return decode_table[(code, length)]
            if length > 15:
                raise ValueError("Huffman code not found after 15 bits")

    while True:
        sym = read_huffman_symbol(ll_decode)

        if sym < 256:  # literal byte
            output.append(sym)

        elif sym == 256:  # end-of-block

            break

        elif sym <= 285:  # length code
            for (min_l, max_l, code, extra_n) in LENGTH_CODE_TABLE:
                if code == sym:
                    extra_v = reader.read_bits(extra_n) if extra_n > 0 else 0  # LSB-first
                    length = min_l + extra_v
                    break

            dist_sym = read_huffman_symbol(dist_decode)
            for (min_d, max_d, dcode, dextra_n) in DISTANCE_CODE_TABLE:
                if dcode == dist_sym:
                    dextra_v = reader.read_bits(dextra_n) if dextra_n > 0 else 0  # LSB-first
                    distance = min_d + dextra_v
                    break

            start = len(output) - distance
            if start < 0:
                raise ValueError(f"Distance {distance} exceeds buffer bounds")
            for i in range(length):
                output.append(output[start + i])

        else:
            raise ValueError(f"Unknown symbol: {sym}")


    with open(output_file_path, "wb") as f:
        f.write(output)



def deflate_compress_bytes(data: bytes) -> bytes:
    with tempfile.NamedTemporaryFile(delete=False) as tmp_in:
        tmp_in.write(data)
        tmp_in_path = tmp_in.name
    tmp_out_path = tmp_in_path + ".out"
    deflate_compress(tmp_in_path, tmp_out_path)
    with open(tmp_out_path, "rb") as f:
        result = f.read()
    os.remove(tmp_in_path)
    os.remove(tmp_out_path)
    return result

def deflate_decompress_bytes(data: bytes) -> bytes:
    with tempfile.NamedTemporaryFile(delete=False) as tmp_in:
        tmp_in.write(data)
        tmp_in_path = tmp_in.name
    tmp_out_path = tmp_in_path + ".out"
    deflate_decompress(tmp_in_path, tmp_out_path)
    with open(tmp_out_path, "rb") as f:
        result = f.read()
    os.remove(tmp_in_path)
    os.remove(tmp_out_path)
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Deflate compressor/decompressor (LZ77 + Huffman)"
    )
    parser.add_argument("mode", choices=["compress", "decompress"],
                        help="Mode: compress or decompress")
    parser.add_argument("input", help="Input file")
    parser.add_argument("output", help="Output file")
    args = parser.parse_args()

    if args.mode == "compress":
        deflate_compress(args.input, args.output)
    else:
        deflate_decompress(args.input, args.output)
