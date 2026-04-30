"""
Module providing a grayscale image class with basic pixel manipulation
and LZW compression/decompression support.


To work with photos we can use from_file method
"""

from PIL import Image, ImageOps
import numpy as np

from lzw import compression, decompression


class GrayscaleImage:
    """
    Represents a grayscale image stored as a 2D NumPy array.

    The class provides methods for pixel manipulation, loading images
    from files, displaying images, and applying LZW compression
    and decompression.
    """

    def __init__(self, nrows, ncols):
        """
        Initialize an empty grayscale image.

        Args:
            nrows (int): Image height (number of rows).
            ncols (int): Image width (number of columns).
        """
        self.data = np.zeros((nrows, ncols), dtype=np.uint8)
        self._ncols = ncols
        self._nrows = nrows

    def width(self):
        """
        Return the width of the image.

        Returns:
            int: Number of columns in the image.
        """
        return self._ncols

    def height(self):
        """
        Return the height of the image.

        Returns:
            int: Number of rows in the image.
        """
        return self._nrows

    def clear(self, value):
        """
        Fill the entire image with a single grayscale value.

        Args:
            value (int): Pixel value between 0 and 255.

        Raises:
            ValueError: If value is outside the valid grayscale range.
        """
        if not 0 <= value <= 255:
            raise ValueError
        self.data[:] = value

    def getitem(self, row, col):
        """
        Get the pixel value at the specified position.

        Args:
            row (int): Row index.
            col (int): Column index.

        Returns:
            int: Pixel value.

        Raises:
            IndexError: If the coordinates are outside the image bounds.
        """
        if not (0 <= row <= self._nrows - 1 and 0 <= col <= self._ncols - 1):
            raise IndexError
        return self.data[row, col]

    def setitem(self, row, col, value):
        """
        Set the pixel value at the specified position.

        Args:
            row (int): Row index.
            col (int): Column index.
            value (int): Pixel value (0–255).

        Raises:
            IndexError: If the coordinates are outside the image bounds.
            ValueError: If the value is outside the valid grayscale range.
        """
        if not (0 <= row <= self._nrows - 1 and 0 <= col <= self._ncols - 1):
            raise IndexError
        if not 0 <= value <= 255:
            raise ValueError
        self.data[row, col] = value

    @classmethod
    def from_file(cls, path):
        """
        Create a GrayscaleImage instance from an image file.

        The image is automatically converted to grayscale.

        Args:
            path (str): Path to the image file.

        Returns:
            GrayscaleImage: Instance containing the loaded image data.
        """
        image = Image.open(path)
        image_grayscale = ImageOps.grayscale(image)
        img_array = np.array(image_grayscale)
        height, width = img_array.shape

        instance = cls(height, width)
        instance.data = img_array.copy()

        return instance

    def show(self):
        """
        Display the image using the default system image viewer.
        """
        Image.fromarray(self.data).show()

    def lzw_compression(self):
        """
        Compress the image using the LZW algorithm.

        Returns:
            list[int]: List of integer codes representing the compressed image.
        """
        return compression(self)

    def lzw_decompression(self, codes):
        """
        Decompress LZW codes and restore the image data.

        Args:
            codes (list[int]): LZW compressed codes.
        """
        output = decompression(codes)
        self.data = np.array(output, dtype=np.uint8).reshape(self._nrows, self._ncols)
