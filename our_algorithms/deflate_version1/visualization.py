import matplotlib.pyplot as plt
from deflate import test_function, test_other

my_time1, my_size_kb1 = test_function('big_test_200kb.txt', 'compressed1.bin')
others1 = test_other('big_test_200kb.txt')

my_time2, my_size_kb2 = test_function('kobzar.txt', 'compressed2.bin')
others2 = test_other('kobzar.txt')

methods = ['zlib', 'bz2', 'lzma', 'My Deflate']
colors  = ['#4C72B0', '#DD8452', '#55A868', '#9B59B6']

def get_times(others, my_time):
    return [
        others['zlib']['time'] * 1000,
        others['bz2']['time']  * 1000,
        others['lzma']['time'] * 1000,
        my_time * 1000,
    ]

def get_sizes(others, my_size_kb):
    return [
        others['zlib']['size'] / 1024,
        others['bz2']['size']  / 1024,
        others['lzma']['size'] / 1024,
        my_size_kb,
    ]

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Порівняння методів стиснення')

axes[0][0].bar(methods, get_times(others1, my_time1), color=colors)
axes[0][0].set_title('Час — big_test_200kb.txt')
axes[0][0].set_ylabel('мілісекунди (мс)')

axes[0][1].bar(methods, get_sizes(others1, my_size_kb1), color=colors)
axes[0][1].set_title('Розмір — big_test_200kb.txt')
axes[0][1].set_ylabel('кілобайти (KB)')

axes[1][0].bar(methods, get_times(others2, my_time2), color=colors)
axes[1][0].set_title('Час — kobzar.txt')
axes[1][0].set_ylabel('мілісекунди (мс)')

axes[1][1].bar(methods, get_sizes(others2, my_size_kb2), color=colors)
axes[1][1].set_title('Розмір — kobzar.txt')
axes[1][1].set_ylabel('кілобайти (KB)')

plt.tight_layout()
plt.show()
