import os
from typer import Argument, Typer

def main_func():
    app = Typer()
    app.add_argument('action', help='Action to perform (info or browse)')
    app.add_argument('--input_file', help='Input file path')
    result = app(__root_dir__='/path/to/your/project/root')
    if result.action == 'info':
        # Handle info action here
        print(f"Info action: {result.input_file}")
    elif result.action == 'browse':
        # Handle browse action here
        print(f"Browsing: {result.input_file}")

if __name__ == '__main__':
    main_func()
