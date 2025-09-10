import os
from rich.console import Console
from typer import Argument, Typer

console = Console()

app = Typer()

@app.command()
def info(input_file: str):
    """Print information about the input file"""
    console.print(f"Info action: {input_file}")

@app.command()
def browse(input_file: str):
    """Browse the input file"""
    console.print(f"Browsing: {input_file}")

if __name__ == '__main__':
    app()
