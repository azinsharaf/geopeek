"""Geopeek CLI module.

Usage:
  geopeek info <path>                  # Rich table output (default)
  geopeek info <path> --format json    # JSON output
  geopeek info <path> --layers         # List layer names only
"""

from enum import Enum

import typer
from rich.console import Console

from geopeek.output.rich_printer import print_rich_table
from geopeek.output.json_printer import print_json
import os

console = Console()

app = typer.Typer()


class OutputFormat(str, Enum):
    table = "table"
    json = "json"


def _normalize_input_path(input_path: str) -> str:
    """Normalize paths to handle trailing separators (e.g., PowerShell backslash)."""
    if not isinstance(input_path, str):
        return input_path
    return input_path.rstrip("/\\")


def _select_handler(input_file: str):
    path = _normalize_input_path(input_file)
    lower = path.lower()
    # Lazy imports to avoid importing all handlers upfront
    if lower.endswith(".shp"):
        from geopeek.handlers.shapefile_handler import ShapefileHandler

        return ShapefileHandler(path)
    if lower.endswith(
        (
            ".tif",
            ".tiff",
            ".jp2",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".img",
            ".vrt",
            ".dem",
        )
    ):
        from geopeek.handlers.raster_handler import RasterHandler

        return RasterHandler(path)
    if lower.endswith(".gdb") or (
        os.path.isdir(path)
        and any(name.lower().endswith(".gdb") for name in os.listdir(path))
    ):
        from geopeek.handlers.gdb_handler import GDBHandler

        return GDBHandler(path)
    raise typer.BadParameter(
        f"Unsupported input type: {input_file}. "
        "Supported: .shp, .gdb, .tif, .tiff, .jp2, .png, .jpg, .img, .vrt, .dem"
    )


def _type_label_for(input_file: str) -> str:
    path = _normalize_input_path(input_file)
    lower = path.lower()
    if lower.endswith(".shp"):
        return "Shapefile"
    if lower.endswith(
        (
            ".tif",
            ".tiff",
            ".jp2",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".img",
            ".vrt",
            ".dem",
        )
    ):
        return "Raster"
    if lower.endswith(".gdb") or (
        os.path.isdir(path)
        and any(name.lower().endswith(".gdb") for name in os.listdir(path))
    ):
        return "Geodatabase"
    return "Input"


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        # Show help when no subcommand is provided
        console.print(ctx.get_help())
        raise typer.Exit(code=0)


@app.command()
def info(
    input_file: str = typer.Argument(..., help="Path to input file or directory."),
    format: OutputFormat = typer.Option(
        OutputFormat.table,
        "--format",
        "-f",
        help="Output format: table or json.",
    ),
    layers: bool = typer.Option(
        False,
        "--layers",
        "-l",
        help="List layer names only.",
    ),
):
    """Print information about the input file."""
    handler = _select_handler(input_file)

    if layers:
        layer_names = handler.get_layers()
        if format == OutputFormat.json:
            print_json({"layers": layer_names})
        else:
            if not layer_names:
                console.print("No layers found.")
            else:
                for name in layer_names:
                    console.print(name)
        return

    metadata = handler.get_info()
    data_type = _type_label_for(input_file)

    if format == OutputFormat.json:
        print_json(metadata)
    else:
        print_rich_table(metadata, f"{data_type} Information")


if __name__ == "__main__":
    app()
