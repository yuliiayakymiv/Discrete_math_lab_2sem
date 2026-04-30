"""
LZW compression for bytes data
"""

def lzw_compress(data: bytes) -> bytes:
    """
    Compress bytes using LZW algorithm.
    Input: bytes
    Output: bytes (compressed)
    """
    if not data:
        return b''

    # Ініціалізація словника: всі байти 0-255
    dictionary = {bytes([i]): i for i in range(256)}
    dict_size = 256

    result = []
    current = bytes()

    for byte in data:
        new_current = current + bytes([byte])
        if new_current in dictionary:
            current = new_current
        else:
            result.append(dictionary[current])
            dictionary[new_current] = dict_size
            dict_size += 1
            current = bytes([byte])

    # Додаємо останній фрагмент
    if current:
        result.append(dictionary[current])

    # Конвертуємо коди в байти
    output = bytearray()
    for code in result:
        # Кодуємо кожен код як 2 байти (16 біт)
        output.append((code >> 8) & 0xFF)
        output.append(code & 0xFF)

    return bytes(output)


def lzw_decompress(data: bytes) -> bytes:
    """
    Decompress LZW compressed bytes.
    Input: bytes (compressed)
    Output: bytes (original)
    """
    if not data:
        return b''

    # Розпаковуємо коди з байтів (по 2 байти на код)
    codes = []
    for i in range(0, len(data), 2):
        if i + 1 < len(data):
            code = (data[i] << 8) | data[i + 1]
            codes.append(code)

    if not codes:
        return b''

    # Ініціалізація словника
    dictionary = {i: bytes([i]) for i in range(256)}
    dict_size = 256

    result = bytearray()
    current = dictionary[codes[0]]
    result.extend(current)

    for code in codes[1:]:
        if code in dictionary:
            entry = dictionary[code]
        elif code == dict_size:
            entry = current + bytes([current[0]])
        else:
            raise ValueError(f"Invalid LZW code: {code}")

        result.extend(entry)

        # Додаємо новий запис до словника
        dictionary[dict_size] = current + bytes([entry[0]])
        dict_size += 1

        current = entry

    return bytes(result)
