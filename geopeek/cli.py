"""Geopeek CLI module.
Note on execution:
  - Run as module: python -m geopeek.cli info "/path/to/dataset.gdb"
  - Run directly: python geopeek/cli.py info "/path/to/dataset.gdb"
"""
from rich.console import Console
import typer
from geopeek.output.rich_printer import print_rich_table
import os

def _normalize_input_path(input_path: str) -> str:
    # Normalize paths to be robust against trailing separators (e.g., PowerShell's trailing backslash)
    if not isinstance(input_path, str):
        return input_path
    return input_path.rstrip("/\\")
    
console = Console()

app = typer.Typer(invoke_without_command=True)

def _select_handler(input_file: str):
    path = _normalize_input_path(input_file)
    lower = path.lower()
    # Lazy imports to avoid importing all handlers upfront
    if lower.endswith(".shp"):
        from geopeek.handlers.shapefile_handler import ShapefileHandler
        return ShapefileHandler(path)
    if lower.endswith((".tif", ".tiff", ".jp2", ".png", ".jpg", ".jpeg", ".gif", ".img", ".vrt", ".dem")):
        from geopeek.handlers.raster_handler import RasterHandler
        return RasterHandler(path)
    if lower.endswith(".gdb") or (os.path.isdir(path) and any(name.lower().endswith(".gdb") for name in os.listdir(path))):
        from geopeek.handlers.gdb_handler import GDBHandler
        return GDBHandler(path)
    raise typer.BadParameter(f"Unsupported input type: {input_file}. Please provide a .gdb directory, a .shp file, or a raster file.")
    
def _type_label_for(input_file: str) -> str:
    path = _normalize_input_path(input_file)
    lower = path.lower()
    if lower.endswith(".shp"):
        return "Shapefile"
    if lower.endswith((".tif", ".tiff", ".jp2", ".png", ".jpg", ".jpeg", ".gif", ".img", ".vrt", ".dem")):
        return "Raster"
    if lower.endswith(".gdb") or (os.path.isdir(path) and any(name.lower().endswith(".gdb") for name in os.listdir(path))):
        return "Geodatabase"
    return "Input"


@app.callback()
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print("No subcommand provided. Use 'info' to get dataset metadata.")
        raise typer.Exit(code=1)

@app.command()
def info(input_file: str = typer.Argument(..., help="Path to input file or directory.")):
    """Print information about the input file"""
    handler = _select_handler(input_file)
    metadata = handler.get_info()
    data_type = _type_label_for(input_file)
    print_rich_table(metadata, f"{data_type} Information")

if __name__ == "__main__":
    app()
