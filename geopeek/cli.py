from rich.console import Console
from typer import Argument, Typer
from geopeek.output.rich_printer import print_rich_table  # Corrected import statement
from geopeek.handlers.gdb_handler import GDBHandler

console = Console()

app = Typer()

@app.command()
def info(input_file: str):
    """Print information about the input file"""
    handler = GDBHandler(input_file)
    handler.print_rich_table()

if __name__ == '__main__':
    app()
