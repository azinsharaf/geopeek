import argparse
from geopeek.core import main

def parse_args():
    parser = argparse.ArgumentParser(description='Geopeek CLI')
    parser.add_argument('action', help='Action to perform (info or browse)')
    parser.add_argument('--input_file', help='Input file path')
    return parser.parse_args()

def main_func(args):
    if args.action == 'info':
        # Handle info action here
        print(f"Info action: {args.input_file}")
    elif args.action == 'browse':
        # Handle browse action here
        print(f"Browsing: {args.input_file}")

if __name__ == '__main__':
    args = parse_args()
    main_func(args)
