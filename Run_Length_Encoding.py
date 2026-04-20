def compress(data):
    """Compress bytes data using RLE"""
    if not data:
        return b''

    compressed = bytearray()
    i = 0

    while i < len(data):
        count = 1
        while i + count < len(data) and data[i + count] == data[i] and count < 255:
            count += 1

        compressed.append(data[i])
        compressed.append(count)
        i += count

    return bytes(compressed)


def decompress(data):
    """Decompress RLE compressed data"""
    if not data:
        return b''

    result = bytearray()

    for i in range(0, len(data), 2):
        if i + 1 >= len(data):
            break
        byte_val = data[i]
        count = data[i + 1]
        result.extend([byte_val] * count)

    return bytes(result)
