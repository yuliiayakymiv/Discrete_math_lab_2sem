"""
Burrows-Wheeler Transform + RLE compression
"""

from algorithms.run_length_encoding import rle_compress, rle_decompress

def _build_sa(data: bytes) -> list[int]:
    n = len(data)
    rank = list(data)
    sa = sorted(range(n), key=lambda i: rank[i])

    k = 1
    while k < n:
        def key(i, k=k):
            return (rank[i], rank[(i + k) % n])  # % n = cyclic wrap
        sa = sorted(range(n), key=key)
        new_rank = [0] * n
        for i in range(1, n):
            new_rank[sa[i]] = new_rank[sa[i-1]] + (key(sa[i]) != key(sa[i-1]))
        rank = new_rank
        if rank[sa[-1]] == n - 1:
            break
        k *= 2
    return sa


def bwt_encode(data: bytes) -> bytes:
    if not data:
        return b""
    n = len(data)
    sa = _build_sa(data)
    last_column = bytes(data[(i - 1) % n] for i in sa)
    original_index = sa.index(0)
    return last_column + original_index.to_bytes(4, "little")


def bwt_decode(data: bytes) -> bytes:
    if not data:
        return b""
    last_column = data[:-4]
    original_index = int.from_bytes(data[-4:], "little")
    n = len(last_column)

    count = [0] * 256
    rank = [0] * n
    for i, b in enumerate(last_column):
        rank[i] = count[b]
        count[b] += 1

    start = [0] * 256
    total = 0
    for sym in range(256):
        start[sym] = total
        total += count[sym]

    result = bytearray(n)
    row = original_index
    for i in range(n - 1, -1, -1):
        b = last_column[row]
        result[i] = b
        row = start[b] + rank[row]

    return bytes(result)


def bwt_compress(data: bytes) -> bytes:
    if not data:
        return b""
    return rle_compress(bwt_encode(data))


def bwt_decompress(data: bytes) -> bytes:
    if not data:
        return b""
    return bwt_decode(rle_decompress(data))
