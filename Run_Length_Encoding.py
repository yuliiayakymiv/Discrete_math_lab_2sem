"""
rle compression
"""
def rle_compress(data):
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

def rle_decompress(data):
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

# if __name__ == "__main__":
#     # Test 1: Simple text
#     original = b"AAAABBBCCCCCCDD"
#     compressed = rle_compress(original)
#     decompressed = rle_decompress(compressed)

#     print("TEST 1: Simple text")
#     print(f"Original:    {original}")
#     print(f"Compressed:  {compressed}")
#     print(f"Decompressed: {decompressed}")
#     print(f"Correct:     {original == decompressed}")
#     print()

#     # Test 2: File test
#     test_file = "test.txt"
#     with open(test_file, 'w') as f:
#         f.write("A" * 100 + "B" * 50 + "C" * 30)

#     with open(test_file, 'rb') as f:
#         original = f.read()

#     compressed = rle_compress(original)
#     decompressed = rle_decompress(compressed)

#     print("TEST 2: File test")
#     print(f"Original size:   {len(original)} bytes")
#     print(f"Compressed size: {len(compressed)} bytes")
#     print(f"Ratio: {len(compressed)/len(original):.2f}")
#     print(f"Correct: {original == decompressed}")
