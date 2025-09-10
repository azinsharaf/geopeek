from rich.console import Console
import typer
from geopeek.output.rich_printer import print_rich_table
import os

console = Console()

app = typer.Typer()

def _select_handler(input_file: str):
    lower = input_file.lower()
    # Lazy imports to avoid importing all handlers upfront
    if lower.endswith(".shp"):
        from geopeek.handlers.shapefile_handler import ShapefileHandler
        return ShapefileHandler(input_file)
    if lower.endswith((".tif", ".tiff", ".jp2", ".png", ".jpg", ".jpeg", ".gif", ".img", ".vrt", ".dem")):
        from geopeek.handlers.raster_handler import RasterHandler
        return RasterHandler(input_file)
    if lower.endswith(".gdb") or (os.path.isdir(input_file) and any(name.lower().endswith(".gdb") for name in os.listdir(input_file))):
        from geopeek.handlers.gdb_handler import GDBHandler
        return GDBHandler(input_file)
    raise typer.BadParameter(f"Unsupported input type: {input_file}. Please provide a .gdb directory, a .shp file, or a raster file.")


@app.command(name="info")
def info_cmd(input_file: str = typer.Argument(..., help="Path to input file or directory.")):
    """Print information about the input file"""
    handler = _select_handler(input_file)
    metadata = handler.get_info()
    print_rich_table(metadata, "Geodatabase Information")

def main():
    app()

if __name__ == "__main__":
    main()
