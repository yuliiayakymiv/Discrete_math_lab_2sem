"""
lab_7_3
"""
import numpy as np
from PIL import Image, ImageOps

class GrayscaleImage:
    """Клас для чорно-білих зображень"""

    def __init__(self, nrows, ncols):
        """Створює зображення nrows x ncols, заповнене 0"""
        self.rows = nrows
        self.cols = ncols
        self.pixels = [[0 for j in range(ncols)] for i in range(nrows)]

    def width(self):
        """Повертає ширину"""
        return self.cols

    def height(self):
        """Повертає висоту"""
        return self.rows

    def clear(self, value):
        """
        Очищує зображення шляхом встановлення кожного пікселя до значення value.
        """
        if 0 <= value <= 255:
            for i in range(self.rows):
                for j in range(self.cols):
                    self.pixels[i][j] = value
        else:
            print("Значення value повинно бути в межах від 0 до 255.")

    def getitem(self, row, col):
        """Повертає значення пікселя"""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.pixels[row][col]

        print("Координати пікселя повинні бути в коректному діапазоні.")
        return None

    def setitem(self, row, col, value):
        """Встановлює значення пікселя"""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            if 0 <= value <= 255:
                self.pixels[row][col] = value
            else:
                print("Значення value повинно бути в межах від 0 до 255.")
        else:
            print("Значення value повинно бути в межах від 0 до 255.")

    @classmethod
    def from_file(cls, path):
        """Завантажує зображення з файлу"""
        image = Image.open(path)
        image_grayscale = ImageOps.grayscale(image)
        img_array = np.array(image_grayscale)

        height, width = img_array.shape
        new_img = cls(height, width)

        for i in range(height):
            for j in range(width):
                new_img.pixels[i][j] = int(img_array[i, j])

        return new_img

    def save(self, path):
        """Зберігає зображення у файл"""
        img_array = np.array(self.pixels)
        new_img = Image.fromarray(img_array)
        new_img.save(path)

    def lzw_compression(self):
        """LZW стиснення"""
        data = []
        for i in range(self.rows):
            for j in range(self.cols):
                data.append(self.pixels[i][j])

        # Словник: ключ - список чисел, значення - код
        dictionary = {}
        for i in range(256):
            dictionary[str([i])] = i

        next_code = 256
        result = []

        current = []
        for pixel in data:
            combined = current + [pixel]
            if str(combined) in dictionary:
                current = combined
            else:
                if current:
                    result.append(dictionary[str(current)])
                dictionary[str(combined)] = next_code
                next_code += 1
                current = [pixel]

        if current:
            result.append(dictionary[str(current)])

        return result

    def lzw_decompression(self, compressed):
        """LZW розпакування"""
        dictionary = {}
        for i in range(256):
            dictionary[i] = [i]

        next_code = 256
        result = []

        prev = compressed[0]
        result.extend(dictionary[prev])

        for code in compressed[1:]:
            if code in dictionary:
                entry = dictionary[code]
            elif code == next_code:
                entry = dictionary[prev] + [dictionary[prev][0]]
            else:
                return

            result.extend(entry)
            dictionary[next_code] = dictionary[prev] + [entry[0]]
            next_code += 1
            prev = code

        idx = 0
        for i in range(self.rows):
            for j in range(self.cols):
                self.pixels[i][j] = result[idx]
                idx += 1
