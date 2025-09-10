from rich.console import Console
from typer import Argument, Typer
from geopeek.handlers.gdb_handler import GDBHandler  # Added this line

console = Console()

app = Typer()

@app.command()
def info(input_file: str):
    """Print information about the input file"""
    handler = GDBHandler(input_file)
    handler.print_info()

if __name__ == '__main__':
    app()
