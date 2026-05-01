"""
Canonical Huffman coding module.
"""
import struct
class HuffmanNode:
    """
    A node in a Huffman binary tree.
    """
    def __init__(self, symbol=None, freq=0, left=None, right=None):
        self.symbol = symbol
        self.freq = freq
        self.left = left
        self.right = right

    def is_leaf(self):
        """
        Return ``True`` if this node is a leaf (carries a symbol).
        """
        return self.symbol is not None

class HuffMan:
    """
    Canonical Huffman encoder/decoder compatible with DEFLATE (RFC 1951).
    """
    def build_tree(self, frequencies: dict) -> HuffmanNode:
        """Build a Huffman binary tree from a symbol-frequency mapping.

        Uses a greedy algorithm (similar to a min-heap):

        1. Create one leaf node per symbol.
        2. Repeatedly merge the two nodes with the lowest frequency into a new
           parent node until only one node (the root) remains.

        Nodes with equal frequencies are ordered by symbol value to produce a
        deterministic tree independent of dict iteration order.

        Returns:
        HuffmanNode
            Root of the constructed Huffman tree.
        """
        if len(frequencies) == 1:                    # single-symbol edge case: depth-1 tree.
            sym = list(frequencies.keys())[0]
            leaf = HuffmanNode(symbol=sym, freq=frequencies[sym])
            dummy = HuffmanNode(symbol=sym, freq=0)
            return HuffmanNode(freq=frequencies[sym], left=leaf, right=dummy)

        nodes = [HuffmanNode(symbol=sym, freq=freq)
                 for sym, freq in frequencies.items()]

        # greedy merge
        while len(nodes) > 1:
            # Sort by (frequency, symbol) for a deterministic result.
            nodes.sort(key=lambda x: (x.freq, x.symbol if x.symbol is not None else -1))
            left = nodes.pop(0)
            right = nodes.pop(0)
            parent = HuffmanNode(
                freq=left.freq + right.freq,
                left=left,
                right=right,
            )
            nodes.append(parent)

        return nodes[0]

    def get_code_lengths(self, root: HuffmanNode) -> dict:
        """Compute the bit-length for each leaf symbol by traversing the tree.

        The bit-length of a symbol equals its depth in the tree (i.e. the
        number of edges from the root to its leaf).  The minimum assigned
        length is 1 (even for the root-level edge case).
        """
        lengths = {}

        def traverse(node, depth):
            if node is None:
                return
            if node.is_leaf():
                lengths[node.symbol] = max(depth, 1)
                return
            traverse(node.left,  depth + 1)
            traverse(node.right, depth + 1)

        traverse(root, 0)
        return lengths

    def build_canonical_codes(self, code_lengths: dict) -> dict:
        """Convert a ``{symbol: length}`` map to canonical Huffman bit codes.

        Algorithm (RFC 1951, section 3.2.2):

        1. Clamp any length > 15 down to 15 (DEFLATE hard limit).
        2. Group symbols by code length; within each group sort by symbol
           value (ascending).
        3. Assign integer codes in order:
           ``code = 0`` for the shortest-length group, then for each step:
           * same length  → ``code += 1``
           * length + 1   → ``code <<= 1`` (prepend a zero bit)
        """
        if not code_lengths:
            return {}

        MAX_LEN = 15  # DEFLATE maximum Huffman code length

        # Clamp any lengths that exceed the DEFLATE limit.
        code_lengths = {sym: min(length, MAX_LEN)
                        for sym, length in code_lengths.items()}

        max_length = max(code_lengths.values())

        # Group symbols by length; sort each group lexicographically.
        symbols_by_length: dict[int, list] = {}
        for sym, length in code_lengths.items():
            symbols_by_length.setdefault(length, []).append(sym)
        for length in symbols_by_length:
            symbols_by_length[length].sort()

        # Assign canonical codes.
        codes: dict[int, tuple] = {}
        code = 0
        for length in range(1, max_length + 1):
            for sym in symbols_by_length.get(length, []):
                codes[sym] = (code, length)
                code += 1
            code <<= 1  # left-shift when moving to the next bit-length level

        return codes

    def build_decode_table(self, codes: dict) -> dict:
        """Build a reverse lookup table for symbol decoding.

        The returned mapping lets a decoder look up a symbol given the bit
        pattern it has read from the stream and the number of bits consumed so
        far.
        """
        return {(code, length): sym for sym, (code, length) in codes.items()}

    def encode_frequencies(self, data: list) -> tuple:            #convinience wraper
        """Full pipeline: count symbol frequencies and produce encode/decode tables.
        """
        frequencies: dict[int, int] = {}
        for sym in data:
            frequencies[sym] = frequencies.get(sym, 0) + 1

        root = self.build_tree(dict(frequencies))
        lengths = self.get_code_lengths(root)
        codes = self.build_canonical_codes(lengths)
        decode_table = self.build_decode_table(codes)
        return codes, decode_table

def huffman_compress(data: bytes) -> bytes:
    huff = HuffMan()
    codes, _ = huff.encode_frequencies(list(data))
    out = bytearray()
    out += struct.pack('<I', len(data))       # зберігаємо оригінальну довжину
    out += struct.pack('<H', len(codes))
    for sym, (code, length) in codes.items():
        out += struct.pack('<BB', sym, length)
    current = 0
    bits = 0
    for byte in data:
        code, length = codes[byte]
        for i in range(length - 1, -1, -1):
            current = (current << 1) | ((code >> i) & 1)
            bits += 1
            if bits == 8:
                out.append(current)
                current = 0
                bits = 0
    if bits > 0:
        out.append(current << (8 - bits))
    return bytes(out)

def huffman_decompress(data: bytes) -> bytes:
    i = 0
    original_len = struct.unpack('<I', data[i:i+4])[0]; i += 4  # читаємо довжину
    num_codes = struct.unpack('<H', data[i:i+2])[0]; i += 2
    code_lengths = {}
    for _ in range(num_codes):
        sym, length = struct.unpack('<BB', data[i:i+2]); i += 2
        code_lengths[sym] = length
    huff = HuffMan()
    codes = huff.build_canonical_codes(code_lengths)
    decode_table = huff.build_decode_table(codes)
    out = bytearray()
    current = 0
    length = 0
    for byte in data[i:]:
        for bit in range(7, -1, -1):
            current = (current << 1) | ((byte >> bit) & 1)
            length += 1
            if (current, length) in decode_table:
                out.append(decode_table[(current, length)])
                current = 0
                length = 0
                if len(out) == original_len:  # зупиняємось вчасно
                    return bytes(out)
    return bytes(out)
