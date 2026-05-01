"""
Data Compression Codec
main
"""
import sys
import argparse
from codec import DataCodec

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
    compress_parser.add_argument('-a', '--algorithm',
                                 choices=['rle', 'huffman', 'lz77', 'lzw', 'lzma', 'deflate', 'bwt'],
                                 help='Compression algorithm (default: rle)')
    compress_parser.add_argument('-v', '--verbose', action='store_true',
                                 help='Verbose output')

    decompress_parser = subparsers.add_parser('decompress', help='Decompress file')
    decompress_parser.add_argument('input', help='Compressed file')
    decompress_parser.add_argument('output', help='Output file')
    decompress_parser.add_argument('-a', '--algorithm',
                                   choices=['rle', 'huffman', 'lz77', 'lzw', 'lzma', 'deflate', 'bwt'],
                                   help='Algorithm for decompression (default: rle)')
    decompress_parser.add_argument('-v', '--verbose', action='store_true',
                                   help='Verbose output')

    test_parser = subparsers.add_parser('test', help='Test algorithm')
    test_parser.add_argument('input', help='File for testing')
    test_parser.add_argument('-a', '--algorithm',
                             choices=['rle', 'huffman', 'lz77', 'lzw', 'lzma', 'deflate', 'bwt'],
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
            for algo in ['rle', 'huffman', 'lz77', 'lzw', 'lzma', 'deflate', 'bwt']:
                codec.test_algorithm(args.input, algo)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
