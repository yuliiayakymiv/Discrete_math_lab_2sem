"""
RLE compression
"""
def rle_compress(data: bytes) -> bytes:
    if not data:
        return b""

    buf = bytearray()
    i = 0
    n = len(data)

    while i < n:
        # check for a repeat run
        run = 1
        while i + run < n and data[i + run] == data[i] and run < 255:
            run += 1

        if run >= 3:
            # worth encoding as a repeat
            buf.append(0x00)
            buf.append(run)
            buf.append(data[i])
            i += run
        else:
            # gather a literal run (stop before a long repeat)
            j = i
            while j < n and j - i < 127:
                # peek: if a repeat of ≥3 starts here, stop the literal run
                rep = 1
                while j + rep < n and data[j + rep] == data[j] and rep < 255:
                    rep += 1
                if rep >= 3:
                    break
                j += 1
            length = j - i
            buf.append(length)
            buf.extend(data[i:i + length])
            i += length

    return bytes(buf)


def rle_decompress(data: bytes) -> bytes:
    if not data:
        return b""

    out = bytearray()
    i = 0
    n = len(data)

    while i < n:
        flag = data[i]; i += 1
        if flag == 0x00:          # repeat packet
            count = data[i];     i += 1
            byte  = data[i];     i += 1
            out.extend(bytes([byte]) * count)
        else:                     # literal packet
            out.extend(data[i:i + flag])
            i += flag

    return bytes(out)
