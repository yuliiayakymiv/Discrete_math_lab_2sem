"""
Burrows-Wheeler Transform (BWT)
алгоритм перестановки даних
"""

from our_algorithms.run_length_encoding import rle_compress, rle_decompress

def bwt_encode(data: bytes) -> bytes:
    """Burrows-Wheeler Transform - кодування"""
    if not data:
        return b''

    n = len(data)
    rotations = [data[i:] + data[:i] for i in range(n)]

    rotations.sort()
    last_column = bytes(rot[-1] for rot in rotations)

    original_index = 0
    for i, rot in enumerate(rotations):
        if rot == data:
            original_index = i
            break

    return last_column + original_index.to_bytes(4, 'little')



def bwt_decode(data: bytes) -> bytes:
    """Burrows-Wheeler Transform - декодування."""
    if not data:
        return b''

    last_column = data[:-4]
    n = len(last_column)
    original_index = int.from_bytes(data[-4:], 'little')

    table = [b''] * n

    for _ in range(n):
        for i in range(n):
            table[i] = bytes([last_column[i]]) + table[i]
        table.sort()

    return table[original_index]

def bwt_compress(data: bytes) -> bytes:
    """
    BWT + RLE - стиснення
    """
    if not data:
        return b''

    bwt_data = bwt_encode(data)
    compressed = rle_compress(bwt_data)

    return compressed


def bwt_decompress(data: bytes) -> bytes:
    """
    Розпакування BWT + RLE
    """
    if not data:
        return b''

    rle_decompressed = rle_decompress(data)
    original = bwt_decode(rle_decompressed)

    return original
