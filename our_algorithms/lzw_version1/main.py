"""
Example of usage

Script demonstrating LZW compression and decompression
of a grayscale image.
"""

from gray_scale_image import GrayscaleImage

img = GrayscaleImage.from_file("image.jpg")

codes = img.lzw_compression()

original_size = img.width() * img.height()
COMPRESSED_SIZE = len(codes)
ratio = original_size / COMPRESSED_SIZE

print(f"Оригінал:   {original_size} пікселів")
print(f"Стиснено:   {COMPRESSED_SIZE} кодів")
print(f"Коефіцієнт: {ratio:.2f}x")

img.lzw_decompression(codes)
img.show()
