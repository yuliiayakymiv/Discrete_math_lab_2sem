"""
Module implementing the LZW (Lempel-Ziv-Welch) compression
and decompression algorithms.
"""


def compression(data):
    """
    Compress grayscale image data using the LZW algorithm.

    Args:
        data (GrayscaleImage): Image object containing pixel data.

    Returns:
        list[int]: List of integer codes representing compressed data.
    """
    dct = {(num,): num for num in range(256)}
    dict_size = 256

    flat = [int(el) for row in data.data for el in row]

    temp = ()
    output = []

    for el in flat:
        key = temp + (el,)
        if key in dct:
            temp = key
            continue

        output.append(dct[temp])
        dct[key] = dict_size
        dict_size += 1
        temp = (el,)

    if temp:
        output.append(dct[temp])

    return output


def decompression(codes: list):
    """
    Decompress LZW codes into the original sequence.

    Args:
        codes (list[int]): Compressed LZW codes.

    Returns:
        list[int]: Decompressed sequence of pixel values.


    """
    dct = {num: (num,) for num in range(256)}
    dict_size = 256
    temp = (codes[0],)

    output = []
    output.append(codes[0])

    for code in codes[1:]:
        if code in dct:
            entry = dct[code]

        elif code == dict_size:
            entry = temp + (temp[0],)

        else:
            raise ValueError

        output.extend(entry)
        dct[dict_size] = temp + (entry[0],)
        dict_size += 1
        temp = entry

    return output
