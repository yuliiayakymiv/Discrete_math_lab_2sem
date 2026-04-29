"""
Data Compression Codec
main
"""
import os
import sys
import argparse
import time

from our_algorithms.run_length_encoding import rle_compress, rle_decompress
# from Huffman import huffman_compress, huffman_decompress
# from LZ77 import lz77_compress, lz77_decompress
# from LZW import lzw_compress, lzw_decompress
# from Burrows_Wheeler_Transform import bwt_compress, bwt_decompress
from our_algorithms.simple_lzma import run_lzma_algorithm
# from DEFLATE import deflate_compress, deflate_decompress

class DataCodec:
    """
    Універсальний кодек для стиснення даних.
    Працює з будь-якими файлами через бінарний режим.
    """

    def __init__(self):
        """Ініціалізація кодеку з доступними алгоритмами"""
        self.algorithms = {
            'rle': {
                'encode': rle_compress,
                'decode': rle_decompress,
                'name': 'Run-Length Encoding',
            },
            # 'huffman': {
            #     'encode': huffman_encode,
            #     'decode': huffman_decode,
            #     'name': 'Huffman Coding',
            # },
            'lzma': {
                'encode': lambda data: run_lzma_algorithm(data, mode='compress'),
                'decode': lambda data: run_lzma_algorithm(data, mode='decompress'),
                'name': 'LZMA',
            },
            # 'lzw': {
            #     'encode': lzw_encode,
            #     'decode': lzw_decode,
            #     'name': 'LZW',
            # }
        }


    def read_file(self, file_path: str) -> bytes:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, 'rb') as f:
            return f.read()

    def write_file(self, file_path: str, data: bytes) -> int:
        with open(file_path, 'wb') as f:
            return f.write(data)

    def get_file_info(self, file_path: str) -> dict:
        return {
            'name': os.path.basename(file_path),
            'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            'exists': os.path.exists(file_path)
        }

    def compress(self, input_file: str, output_file: str, algorithm: str, verbose: bool = True):
        if algorithm not in self.algorithms:
            raise ValueError(f"Unknown algorithm: {algorithm}")

        file_info = self.get_file_info(input_file)
        if not file_info['exists']:
            raise FileNotFoundError(f"File not exists: {input_file}")

        if verbose:
            print(f"\n{'='*50}")
            print(f"COMPRESSION")
            print(f"{'-'*50}")
            print(f"File: {file_info['name']}")
            print(f"Size: {file_info['size']:,} bytes ({file_info['size']/1024:.2f} KB)")
            print(f"Algorithm: {self.algorithms[algorithm]['name']}")
            print(f"{'-'*50}")

        original_data = self.read_file(input_file)
        original_size = len(original_data)

        encode_func = self.algorithms[algorithm]['encode']
        start_time = time.time()
        compressed_data = encode_func(original_data)
        compress_time = time.time() - start_time

        self.write_file(output_file, compressed_data)
        compressed_size = len(compressed_data)

        ratio = compressed_size / original_size if original_size > 0 else 1.0

        if verbose:
            print(f"\nRESULTS:")
            print(f"  Original:  {original_size:>10,} bytes")
            print(f"  Compressed: {compressed_size:>10,} bytes")
            print(f"  Ratio: {ratio:.3f}x")
            print(f"  Time: {compress_time*1000:.2f} ms")
            print(f"\nSaved: {output_file}")
            print(f"{'-'*50}\n")

        return original_size, compressed_size, compress_time

    def decompress(self, input_file: str, output_file: str, algorithm: str = 'rle', verbose: bool = True):
        if algorithm not in self.algorithms:
            raise ValueError(f"Unknown algorithm: {algorithm}")

        file_info = self.get_file_info(input_file)
        if not file_info['exists']:
            raise FileNotFoundError(f"File not exists: {input_file}")

        if verbose:
            print(f"\n{'-'*50}")
            print(f"DECOMPRESSION")
            print(f"{'='*50}")
            print(f"File: {file_info['name']}")
            print(f"Size: {file_info['size']:,} bytes ({file_info['size']/1024:.2f} KB)")
            print(f"Algorithm: {self.algorithms[algorithm]['name']}")
            print(f"{'-'*50}")

        compressed_data = self.read_file(input_file)
        compressed_size = len(compressed_data)

        decode_func = self.algorithms[algorithm]['decode']
        start_time = time.time()
        decompressed_data = decode_func(compressed_data)
        decompress_time = time.time() - start_time

        self.write_file(output_file, decompressed_data)
        decompressed_size = len(decompressed_data)

        if verbose:
            print(f"\nRESULTS:")
            print(f"  Compressed:   {compressed_size:>10,} bytes")
            print(f"  Decompressed: {decompressed_size:>10,} bytes")
            print(f"  Time: {decompress_time*1000:.2f} ms")
            print(f"\nSaved: {output_file}")
            print(f"{'-'*50}\n")

        return compressed_size, decompressed_size, decompress_time

    def list_algorithms(self) -> None:
        print(f"\n{'-'*50}")
        print("AVAILABLE ALGORITHMS")
        print(f"{'-'*50}")
        for key, algo in self.algorithms.items():
            print(f"  {key.upper()} - {algo['name']}")
        print(f"{'-'*50}\n")

    def test_algorithm(self, test_file: str, algorithm: str = 'rle') -> dict:
        print(f"\nTESTING {algorithm.upper()}")
        print(f"{'-'*50}")

        temp_compressed = f"_temp_{algorithm}.compressed"
        temp_decompressed = f"_temp_{algorithm}.restored"

        try:
            orig_size, comp_size, comp_time = self.compress(
                test_file, temp_compressed, algorithm, verbose=False
            )

            comp_size2, decomp_size, decomp_time = self.decompress(
                temp_compressed, temp_decompressed, algorithm, verbose=False
            )

            original_data = self.read_file(test_file)
            restored_data = self.read_file(temp_decompressed)
            is_valid = original_data == restored_data

            results = {
                'algorithm': algorithm,
                'original_size': orig_size,
                'compressed_size': comp_size,
                'ratio': comp_size / orig_size if orig_size > 0 else 1.0,
                'compress_time_ms': comp_time * 1000,
                'decompress_time_ms': decomp_time * 1000,
                'is_valid': is_valid
            }

            print(f"\nRESULTS:")
            print(f"  Correct: {'PASS' if is_valid else 'FAIL'}")
            print(f"  Size: {orig_size:,} -> {comp_size:,} bytes")
            print(f"  Ratio: {results['ratio']:.3f}x")
            print(f"  Compress time: {results['compress_time_ms']:.2f} ms")
            print(f"  Decompress time: {results['decompress_time_ms']:.2f} ms")

            return results

        finally:
            for temp_file in [temp_compressed, temp_decompressed]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)


def main():
    parser = argparse.ArgumentParser(
        description='Universal Data Compression Codec',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python main.py compress video.mp4 compressed.bin -a rle
  python main.py decompress compressed.bin restored.mp4 -a rle
  python main.py list-algorithms
  python main.py test test.txt -a rle
        '''
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    compress_parser = subparsers.add_parser('compress', help='Compress file')
    compress_parser.add_argument('input', help='Input file')
    compress_parser.add_argument('output', help='Output file')
    compress_parser.add_argument('-a', '--algorithm', default='rle',
                                 choices=['rle', 'huffman', 'lz77', 'lzw', 'lzma'],
                                 help='Compression algorithm (default: rle)')
    compress_parser.add_argument('-v', '--verbose', action='store_true',
                                 help='Verbose output')

    decompress_parser = subparsers.add_parser('decompress', help='Decompress file')
    decompress_parser.add_argument('input', help='Compressed file')
    decompress_parser.add_argument('output', help='Output file')
    decompress_parser.add_argument('-a', '--algorithm', default='rle',
                                   choices=['rle', 'huffman', 'lz77', 'lzw', 'lzma'],
                                   help='Algorithm for decompression (default: rle)')
    decompress_parser.add_argument('-v', '--verbose', action='store_true',
                                   help='Verbose output')

    test_parser = subparsers.add_parser('test', help='Test algorithm')
    test_parser.add_argument('input', help='File for testing')
    test_parser.add_argument('-a', '--algorithm', default='rle',
                             choices=['rle', 'huffman', 'lz77', 'lzw', 'lzma'],
                             help='Algorithm to test')

    subparsers.add_parser('list-algorithms', help='Show available algorithms')

    benchmark_parser = subparsers.add_parser('benchmark', help='Compare all algorithms')
    benchmark_parser.add_argument('input', help='File for benchmark')

    args = parser.parse_args()

    codec = DataCodec()

    if args.command == 'compress':
        try:
            codec.compress(args.input, args.output, args.algorithm, args.verbose)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'decompress':
        try:
            codec.decompress(args.input, args.output, args.algorithm, args.verbose)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'test':
        try:
            codec.test_algorithm(args.input, args.algorithm)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'list-algorithms':
        codec.list_algorithms()

    elif args.command == 'benchmark':
        try:
            print(f"\nBENCHMARK - ALL ALGORITHMS")
            print(f"{'-'*50}")
            for algo in ['rle', 'huffman', 'lz77', 'lzw', 'lzma']:
                codec.test_algorithm(args.input, algo)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
