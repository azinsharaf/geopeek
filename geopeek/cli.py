import typer
from rich.table import Table
from rich.console import Console

from .main import GeoPeek

app = typer.Typer()
console = Console()

@app.command()
def info(gdb_path: str):
    """Get info about a GIS file geodatabase."""
    geopeek = GeoPeek(gdb_path)
    feature_classes = geopeek.list_feature_classes()
    table = Table(title=f"Feature Classes in {gdb_path}")
    table.add_column("Feature Class")
    for fc in feature_classes:
        table.add_row(fc)
    console.print(table)

if __name__ == "__main__":
    app()
