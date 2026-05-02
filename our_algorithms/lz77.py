"""
LZ77 compression / decompression module.
"""
import struct
WINDOW_SIZE   = 32_768  # 32 KB sliding look-back window
MAX_MATCH_LEN = 258     # maximum match length
MIN_MATCH_LEN = 3       # minimum match length worth referencing


class LZ77Token:
    """Either a literal byte or a (distance, length) back-reference.

    Provide ``literal`` for a raw byte, or ``distance`` + ``length`` for a
    back-reference. Overlapping references (``distance < length``) are valid.
    """

    def __init__(self, literal=None, distance=None, length=None):
        self.literal  = literal   # int 0-255
        self.distance = distance  # int 1-32768
        self.length   = length    # int 3-258

    def is_literal(self):
        """Return ``True`` if this token is a literal byte."""
        return self.literal is not None

    def __repr__(self):
        if self.is_literal():
            return f"Lit({self.literal})"
        return f"Ref(dist={self.distance}, len={self.length})"


class LZ77:
    """LZ77 sliding-window compressor and decompressor.
    """
    def compress(self, data: bytes) -> list:
        """Compress bytes into a list of :class:`LZ77Token`.

        Greedy single-pass scan: at each position searches the window for the
        longest match (>= ``MIN_MATCH_LEN``). Emits a back-reference on a hit,
        a literal otherwise.

        Returns
        list[LZ77Token]
            Token stream that reconstructs ``data`` via :meth:`decompress`.
        """
        tokens = []
        pos = 0
        n = len(data)
        hash_table: dict[bytes, list[int]] = {}

        while pos < n:
            best_length = 0
            best_distance = 0

            if pos + MIN_MATCH_LEN <= n:
                candidate = pos - 1
                while candidate >= window_start:
                    match_len = 0
                    while (
                        match_len < MAX_MATCH_LEN
                        and pos + match_len < n
                        and data[candidate + match_len] == data[pos + match_len]
                    ):
                        match_len += 1

                    if match_len > best_length:
                        best_length   = match_len
                        best_distance = pos - candidate

                    if best_length == MAX_MATCH_LEN:
                        break

                    candidate -= 1

            if best_length >= MIN_MATCH_LEN:
                tokens.append(LZ77Token(distance=best_distance, length=best_length))
                pos += best_length
            else:
                tokens.append(LZ77Token(literal=data[pos]))
                pos += 1

        return tokens

    def decompress(self, tokens: list) -> bytes:
        """Reconstruct the original bytes from a token list.

        Returns
        bytes
            Decompressed data identical to the original input.
        """
        output = bytearray()
        for token in tokens:
            if token.is_literal():
                output.append(token.literal)
            else:
                start = len(output) - token.distance
                for i in range(token.length):
                    output.append(output[start + i])
        return bytes(output)

def lz77_compress(data: bytes) -> bytes:
    tokens = LZ77().compress(data)
    out = bytearray()
    for token in tokens:
        if token.is_literal():
            out.append(0)
            out.append(token.literal)
        else:
            out.append(1)
            out += struct.pack('<HH', token.distance, token.length)
    return bytes(out)

def lz77_decompress(data: bytes) -> bytes:
    tokens = []
    i = 0
    while i < len(data):
        kind = data[i]; i += 1
        if kind == 0:
            tokens.append(LZ77Token(literal=data[i])); i += 1
        else:
            dist, length = struct.unpack('<HH', data[i:i+4]); i += 4
            tokens.append(LZ77Token(distance=dist, length=length))
    return LZ77().decompress(tokens)
