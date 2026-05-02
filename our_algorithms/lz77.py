"""
LZ77 compression / decompression module.
"""
import struct
WINDOW_SIZE = 32_768  # 32 KB sliding look-back window
MAX_MATCH_LEN = 258   # maximum match length
MIN_MATCH_LEN = 3     # minimum match length worth referencing
MAX_CANDIDATES = 32   # how many hash bucket entries to check per position


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
                key = data[pos : pos + MIN_MATCH_LEN]
                bucket = hash_table.setdefault(key, [])
                candidates = bucket

                # only slice if the bucket is actually oversized
                cands = candidates if len(candidates) <= MAX_CANDIDATES else candidates[-MAX_CANDIDATES:]

                for candidate in reversed(cands):
                    if pos - candidate > WINDOW_SIZE:
                        break  # candidates are stored oldest-first, so we can stop early

                    # replaced byte-by-byte Python loop with slice comparison
                    a = data[pos : pos + MAX_MATCH_LEN]
                    b = data[candidate : candidate + MAX_MATCH_LEN]
                    match_len = next(
                        (i for i, (x, y) in enumerate(zip(a, b)) if x != y),
                        min(len(a), len(b)),
                    )

                    if match_len > best_length:
                        best_length   = match_len
                        best_distance = pos - candidate

                    if best_length == MAX_MATCH_LEN:
                        break

                if len(bucket) > MAX_CANDIDATES * 2:
                    del bucket[:MAX_CANDIDATES]  # evict oldest entries outside the window
                bucket.append(pos)

            if best_length >= MIN_MATCH_LEN:
                tokens.append(LZ77Token(distance=best_distance, length=best_length))

                # limit intermediate position registration to first 3 skips
                for skip in range(1, min(best_length, 4)):
                    p = pos + skip
                    if p + MIN_MATCH_LEN <= n:
                        k = data[p : p + MIN_MATCH_LEN]
                        b = hash_table.setdefault(k, [])
                        b.append(p)

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
    
