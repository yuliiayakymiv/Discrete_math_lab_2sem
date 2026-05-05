"""
LZW
"""

MAX_BITS = 16
CLEAR_CODE = 256
EOF_CODE = 257
FIRST_CODE = 258


def lzw_compress(data: bytes) -> bytes:
    """
    lzw_compress
    """

    if not data:
        return b""

    table = {bytes([i]): i for i in range(256)}
    next_code, width = FIRST_CODE, 9

    tagged = [(CLEAR_CODE, width)]
    prefix = bytes([data[0]])

    for byte in data[1:]:
        combined = prefix + bytes([byte])
        if combined in table:
            prefix = combined
        else:
            tagged.append((table[prefix], width))
            if next_code < (1 << MAX_BITS):
                table[combined] = next_code
                next_code += 1
                if next_code > (1 << width) and width < MAX_BITS:
                    width += 1
            else:
                tagged.append((CLEAR_CODE, width))
                table = {bytes([i]): i for i in range(256)}
                next_code, width = FIRST_CODE, 9
            prefix = bytes([byte])

    tagged.append((table[prefix], width))
    tagged.append((EOF_CODE, width))

    bits, nbits, buf = 0, 0, bytearray()
    for code, w in tagged:
        bits |= code << nbits
        nbits += w
        while nbits >= 8:
            buf.append(bits & 0xFF)
            bits >>= 8; nbits -= 8
    if nbits:
        buf.append(bits & 0xFF)

    return bytes(buf)


def lzw_decompress(data: bytes) -> bytes:
    """
    lzw_decompress
    """

    if not data:
        return b""

    pos, bits, nbits = 0, 0, 0

    def read(width):
        nonlocal pos, bits, nbits
        while nbits < width:
            bits |= data[pos] << nbits
            nbits += 8; pos += 1
        value = bits & ((1 << width) - 1)
        bits >>= width; nbits -= width
        return value

    table = {i: bytes([i]) for i in range(256)}
    next_code, width = FIRST_CODE, 9

    assert read(width) == CLEAR_CODE
    output, prev = bytearray(), None

    while True:
        code = read(width)
        if code == EOF_CODE:
            break
        if code == CLEAR_CODE:
            table = {i: bytes([i]) for i in range(256)}
            next_code, width, prev = FIRST_CODE, 9, None
            continue

        entry = table[code] if code in table else (prev + bytes([prev[0]]) if prev else bytes([code & 0xFF]))
        output.extend(entry)

        if prev is not None and next_code < (1 << MAX_BITS):
            table[next_code] = prev + bytes([entry[0]])
            next_code += 1
            if next_code >= (1 << width) and width < MAX_BITS:
                width += 1

        prev = entry

    return bytes(output)
