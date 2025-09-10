import argparse
from geopeek.core import main

def parse_args():
    parser = argparse.ArgumentParser(description='Geopeek CLI')
    parser.add_argument('input_file', help='Input file path')
    return parser.parse_args()

def main_func(args):
    # Call the main function from core module
    main.main(args.input_file)

if __name__ == '__main__':
    args = parse_args()
    main_func(args)
