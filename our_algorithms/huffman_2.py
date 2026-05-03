import heapq
import struct
from collections import Counter

class HuffmanNode:
    """
    Represents a node in the Huffman Tree.
    Used for both leaf nodes (containing symbols) and internal nodes.
    """
    def __init__(self, symbol=None, freq=0, left=None, right=None):
        self.symbol = symbol
        self.freq = freq
        self.left = left
        self.right = right

    def __lt__(self, other):
        return self.freq < other.freq

class HuffmanCoder:
    """
    A logic provider for building Huffman trees and generating canonical codes.
    Canonical codes ensure that we only need to store code lengths in the file header.
    """
    def build_tree(self, frequencies):
        heap = [HuffmanNode(sym, freq) for sym, freq in frequencies.items()]
        heapq.heapify(heap)

        if len(heap) == 1:
            node = heapq.heappop(heap)
            return HuffmanNode(freq=node.freq, left=node)

        while len(heap) > 1:
            left = heapq.heappop(heap)
            right = heapq.heappop(heap)
            parent = HuffmanNode(freq=left.freq + right.freq, left=left, right=right)
            heapq.heappush(heap, parent)

        return heap[0]

    def get_lengths(self, root):
        lengths = {}
        def _traverse(node, depth):
            if node is None: return
            if node.symbol is not None:
                lengths[node.symbol] = max(depth, 1)
                return
            _traverse(node.left, depth + 1)
            _traverse(node.right, depth + 1)
        _traverse(root, 0)
        return lengths

    def get_canonical_codes(self, lengths):
        if not lengths: return {}
        max_len = max(lengths.values())
        nodes_by_len = {}
        for sym, l in lengths.items():
            nodes_by_len.setdefault(l, []).append(sym)

        codes = {}
        code = 0
        for l in range(1, max_len + 1):
            if l in nodes_by_len:
                for sym in sorted(nodes_by_len[l]):
                    codes[sym] = (code, l)
                    code += 1
            code <<= 1
        return codes

def huffman_compress(data: bytes) -> bytes:
    """
    Compresses raw bytes into Huffman encoded bytes.
    Format: [Original Size (4B)][Table Size (2B)][Table Data...][Encoded Bits...]
    """
    if not data:
        return struct.pack('<I', 0)

    freqs = Counter(data)
    coder = HuffmanCoder()
    root = coder.build_tree(freqs)
    lengths = coder.get_lengths(root)
    codes = coder.get_canonical_codes(lengths)

    output = bytearray()
    output += struct.pack('<I', len(data))
    output += struct.pack('<H', len(lengths))

    for sym, length in sorted(lengths.items()):
        output += struct.pack('<BB', sym, length)

    bit_buffer = 0
    bit_count = 0
    for byte in data:
        code, length = codes[byte]
        for i in range(length - 1, -1, -1):
            bit_buffer = (bit_buffer << 1) | ((code >> i) & 1)
            bit_count += 1
            if bit_count == 8:
                output.append(bit_buffer)
                bit_buffer = 0
                bit_count = 0

    if bit_count > 0:
        output.append(bit_buffer << (8 - bit_count))

    return bytes(output)

def huffman_decompress(data: bytes) -> bytes:
    """
    Decompresses Huffman encoded bytes back to original format.
    Uses the canonical length table to reconstruct the code mapping.
    """
    if len(data) < 4: return b""

    ptr = 0
    original_size = struct.unpack('<I', data[ptr:ptr+4])[0]; ptr += 4
    if original_size == 0: return b""

    num_entries = struct.unpack('<H', data[ptr:ptr+2])[0]; ptr += 2
    lengths = {}
    for _ in range(num_entries):
        sym, l = struct.unpack('<BB', data[ptr:ptr+2]); ptr += 2
        lengths[sym] = l

    coder = HuffmanCoder()
    codes = coder.get_canonical_codes(lengths)
    rev_codes = {(val, length): sym for sym, (val, length) in codes.items()}

    result = bytearray()
    curr_val = 0
    curr_len = 0

    for i in range(ptr, len(data)):
        byte = data[i]
        for bit_idx in range(7, -1, -1):
            bit = (byte >> bit_idx) & 1
            curr_val = (curr_val << 1) | bit
            curr_len += 1

            if (curr_val, curr_len) in rev_codes:
                result.append(rev_codes[(curr_val, curr_len)])
                curr_val = 0
                curr_len = 0
                if len(result) == original_size:
                    return bytes(result)

    return bytes(result)
