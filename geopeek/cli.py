from rich.console import Console
from typer import Typer
from geopeek.handlers.gdb_handler import GDBHandler

console = Console()

app = Typer()


@app.command()
def info(input_file: str):
    """Print information about the input file"""
    handler = GDBHandler(input_file)
    metadata = handler.get_info()  # Updated this line
    print_rich_table(metadata, "Geodatabase Information")
