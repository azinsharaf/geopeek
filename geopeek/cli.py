from rich.console import Console
from typer import Argument, Typer
from geopeek.output.json_printer import print_json  # Import the correct function

console = Console()

app = Typer()

@app.command()
def info(input_file: str):
    """Print information about the input file"""
    handler = GDBHandler(input_file)
    handler.print_json()  # Update this line to use the correct function
