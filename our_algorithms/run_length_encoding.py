"""
rle compression
"""
def rle_compress(data: bytes) -> bytes:
    """групує однакові байти разом"""
    if not data:
        return b''

    encoded = bytearray()
    i = 0
    while i < len(data):
        count = 1
        while i + count < len(data) and data[i + count] == data[i] and count < 255:
            count += 1

        if count > 1:
            encoded.append(count)
            encoded.append(data[i])
        else:
            encoded.append(1)
            encoded.append(data[i])

        i += count
    return bytes(encoded)


def rle_decompress(data):
    """Decompress RLE compressed data"""
    decoded = bytearray()
    i = 0
    while i < len(data):
        count = data[i]
        byte_val = data[i + 1]
        decoded.extend([byte_val] * count)
        i += 2
    return bytes(decoded)
