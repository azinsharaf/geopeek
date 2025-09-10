from rich.console import Console
from typer import Argument, Typer
from .main import GeoPeek
import sys

app = Typer()
console = Console()

@app.command()
def info(gdb_path: str = Argument(..., help="Path to the GIS file geodatabase")):
    """Get info about the GIS file geodatabase."""
    try:
        geopeek = GeoPeek(gdb_path)
        feature_classes = geopeek.list_feature_classes()
        if not feature_classes:
            console.print(f"No feature classes found in {gdb_path}", style="bold red")
            return
        table = Table(title=f"Feature Classes in {gdb_path}")
        table.add_column("Feature Class")
        for fc in feature_classes:
            table.add_row(fc)
        console.print(table)
    except Exception as e:
        console.print(f"Error: {e}", style="bold red")

@app.command()
def browse(gdb_path: str = Argument(..., help="Path to the GIS file geodatabase")):
    """Launch the TUI for browsing a GIS dataset."""
    pass
