from rich.console import Console
from typer import Typer
from geopeek.handlers.gdb_handler import GDBHandler
from geopeek.output.rich_printer import print_rich_table

console = Console()

app = Typer()


@app.command()
def info(input_file: str):
    """Print information about the input file"""
    handler = GDBHandler(input_file)
    metadata = handler.get_gdb_info()  # Updated this line
    print_rich_table(metadata, "Geodatabase Information")
