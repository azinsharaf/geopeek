from rich.console import Console
from typer import Argument, Typer
from geopeek.output.json_printer import print_json  # Import the correct function
from geopeek.handlers.gdb_handler import GDBHandler
console = Console()

app = Typer()

@app.command()
def info(input_file: str):
    """Print information about the input file"""
    handler = GDBHandler(input_file)
    handler.print_info()  # Update this line to use the correct function
