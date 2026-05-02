"""
Модуль адаптивного арифметичного кодування.

Цей модуль реалізує арифметичне стиснення даних з використанням адаптивної моделі ймовірностей.
На відміну від статичного кодування, модель оновлюється динамічно після кожного прочитаного символу.
Для оптимізації обчислень префіксних сум та швидкого оновлення частот використовується Дерево Фенвіка.

Основні переваги:
1. Наближається до теоретичної межі стиснення (aka ентропії) краще за метод Хаффмана.
2. Не потребує передачі таблиці частот у заголовку файлу (адаптивність).
3. Висока швидкість операцій завдяки складності O(log N) на символ.
"""
class FenwickTree:
    """Prefix sum tree
    Використовується для ефективного зберігання (query) та оновлення (update) накопичувальних частот символів.
    Дозволяє отримувати префіксну суму (кількість символів, що зустрілися раніше)
    та оновлювати частоту конкретного символу за час O(log N).
    """
    def __init__(self, size):
        """Ініціалізує дерево нулями.
        :param size: Кількість елементів (символів), що зберігаються в дереві."""
        self.n = size
        self.tree = [0] * (size + 1)

    def update(self, i, delta=1):
        """
        Збільшує частоту символу на позиції i.
        :param i: Індекс символу (1-indexed).
        :param delta: Значення, на яке збільшується частота (за замовчуванням 1).
        """
        while i <= self.n:
            self.tree[i] += delta
            i += i & (-i)

    def query(self, i):
        """
        Обчислює префіксну суму частот від 1 до i включно.
        Це відповідає значенню "Cumulative Frequency" в арифметичному кодуванні.
        :param i: Індекс символу.
        :return: Накопичена частота.
        """
        s = 0
        while i > 0:
            s += self.tree[i]
            i -= i & (-i)
        return s

    def find(self, target):
        """Бінарний пошук: перший i такий що query(i) > target — O(log n)

        Виконує швидкий пошук символу за його накопиченою частотою.
        Використовує двійковий підйом (binary lifting) по дереву для досягнення складності O(log N).
        Використовується при декомпресії для визначення, якому символу належить інтервал.
        :param target: Значення частоти, яку потрібно знайти.
        :return: Індекс символу (0-indexed).
        """
        pos = 0
        log = self.n.bit_length()
        for i in range(log, -1, -1):
            npos = pos + (1 << i)
            if npos <= self.n and self.tree[npos] <= target:
                target -= self.tree[npos]
                pos = npos
        return pos  # 0-indexed символ


class ArithmeticAlgorithm:
    """
    Клас, що реалізує логіку арифметичного кодування з використанням цілочисельної арифметики.

    Алгоритм представляє потік даних як єдине дробове число в інтервалі [0, 1).
    З кожним новим символом інтервал звужується пропорційно ймовірності цього символу.
    Для запобігання переповненню використовується техніка бітової нормалізації (E1, E2, E3 умови).
    """
    def __init__(self, precision=32):
        """
        Налаштовує точність обчислень.
        :param precision: Розрядність цілих чисел (зазвичай 32 або 64 біти).
        """
        self.PRECISION = precision
        self.MAX_VALUE = (1 << precision) - 1
        self.ONE_FOURTH = (self.MAX_VALUE + 1) // 4
        self.ONE_HALF = 2 * self.ONE_FOURTH
        self.THREE_FOURTHS = 3 * self.ONE_FOURTH
        self.bit_buffer = 0
        self.bit_count = 0

    def _make_model(self):
        """
        Створює початкову адаптивну модель.
        Алфавіт складається з 256 байтів + 1 службовий символ EOF (End Of File).
        Початкова частота кожного символу 1 (Laplace smoothing).
        257 символів (0-255 + EOF=256), кожен з початковою частотою 1"""
        ft = FenwickTree(257)
        for i in range(1, 258):  # 1-indexed
            ft.update(i, 1)
        return ft, 257  # total_freq

    def _output_bit(self, res, bit):
        """Додає один біт до результату, групуючи біти у байти."""
        self.bit_buffer = (self.bit_buffer << 1) | bit
        self.bit_count += 1
        if self.bit_count == 8:
            res.append(self.bit_buffer)
            self.bit_buffer = 0
            self.bit_count = 0

    def _output_bits(self, res, bit, n):
        """Виводить біт та N протилежних йому бітів (обробка умови E3)."""
        self._output_bit(res, bit)
        for _ in range(n):
            self._output_bit(res, 1 - bit)

    def compress(self, data: bytes) -> bytes:
        """
        Стискає вхідні байти в арифметичний код.

        Процес включає:
        1. Звуження інтервалу [low, high] для кожного символу.
        2. Нормалізацію інтервалу, коли він стає занадто малим.
        3. Оновлення частот символів у Дереві Фенвіка після кожного кроку.
        4. Додавання символу EOF в кінці для коректної декомпресії.
        """
        self.bit_buffer = 0
        self.bit_count = 0

        ft, total_freq = self._make_model()
        low, high = 0, self.MAX_VALUE
        bits_to_follow = 0
        res = bytearray()

        for char in list(data) + [256]:
            sym = char + 1  # 1-indexed у Fenwick Tree

            char_low_count = ft.query(sym - 1)      # сума [1..sym-1]
            char_high_count = ft.query(sym)          # сума [1..sym]

            range_width = high - low + 1
            high = low + (range_width * char_high_count) // total_freq - 1
            low = low + (range_width * char_low_count) // total_freq

            #Normalisation
            while True:
                if high < self.ONE_HALF:
                    self._output_bits(res, 0, bits_to_follow)
                    bits_to_follow = 0
                elif low >= self.ONE_HALF:
                    self._output_bits(res, 1, bits_to_follow)
                    bits_to_follow = 0
                    low -= self.ONE_HALF
                    high -= self.ONE_HALF
                elif low >= self.ONE_FOURTH and high < self.THREE_FOURTHS:
                    bits_to_follow += 1
                    low -= self.ONE_FOURTH
                    high -= self.ONE_FOURTH
                else:
                    break
                low = (low << 1) & self.MAX_VALUE
                high = ((high << 1) | 1) & self.MAX_VALUE

            ft.update(sym, 1)  # O(log 257)
            total_freq += 1

        bits_to_follow += 1
        if low < self.ONE_FOURTH:
            self._output_bits(res, 0, bits_to_follow)
        else:
            self._output_bits(res, 1, bits_to_follow)

        if self.bit_count > 0:
            res.append(self.bit_buffer << (8 - self.bit_count))

        return bytes(res)

    def decompress(self, compressed_data: bytes) -> bytes:
        """
        Відновлює оригінальні дані з арифметичного коду.

        Використовує ту саму адаптивну модель (Дерево Фенвіка), що і компресор.
        На кожному кроці визначає, в який інтервал частот потрапляє поточне
        число (value), видає відповідний символ і оновлює модель.
        Процес триває до зустрічі символу EOF (256).
        """
        if not compressed_data:
            return b""

        def get_bits(data):
            for byte in data:
                for i in range(7, -1, -1):
                    yield (byte >> i) & 1

        bit_gen = get_bits(compressed_data)
        ft, total_freq = self._make_model()

        low, high = 0, self.MAX_VALUE
        value = 0
        for _ in range(self.PRECISION):
            value = (value << 1) | next(bit_gen, 0)

        result = bytearray()
        while True:
            range_width = high - low + 1
            scaled_value = ((value - low + 1) * total_freq - 1) // range_width

            # O(log 257) пошук через Fenwick Tree
            char = ft.find(scaled_value)  # 0-indexed

            if char == 256:
                break
            result.append(char)

            sym = char + 1
            char_low_count = ft.query(sym - 1)
            char_high_count = ft.query(sym)

            high = low + (range_width * char_high_count) // total_freq - 1
            low = low + (range_width * char_low_count) // total_freq

            while True:
                if high < self.ONE_HALF:
                    pass
                elif low >= self.ONE_HALF:
                    value -= self.ONE_HALF
                    low -= self.ONE_HALF
                    high -= self.ONE_HALF
                elif low >= self.ONE_FOURTH and high < self.THREE_FOURTHS:
                    value -= self.ONE_FOURTH
                    low -= self.ONE_FOURTH
                    high -= self.ONE_FOURTH
                else:
                    break
                low = (low << 1) & self.MAX_VALUE
                high = ((high << 1) | 1) & self.MAX_VALUE
                value = ((value << 1) | next(bit_gen, 0)) & self.MAX_VALUE

            ft.update(sym, 1)  # O(log 257)
            total_freq += 1

        return bytes(result)


def arithmetic_compress(data):
    return ArithmeticAlgorithm().compress(data)
def arithmetic_decompress(data):
    return ArithmeticAlgorithm().decompress(data)
