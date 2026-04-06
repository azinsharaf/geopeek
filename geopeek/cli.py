"""Geopeek CLI module.

Usage:
  geopeek                              # Launch TUI with file picker
  geopeek browse <path>                # Launch TUI on dataset
  geopeek info <path>                  # Rich table output (default)
  geopeek info <path> --format json    # JSON output
  geopeek info <path> --layers         # List layer names only
  geopeek peek <path>                  # Preview data (first 10 rows)
  geopeek peek <path> --limit 20       # Preview more rows
  geopeek schema <path>                # Show field/band schema
  geopeek extent <path>                # Show bounding box extent
"""

from enum import Enum

import typer
from rich.console import Console

from geopeek.output.rich_printer import (
    print_rich_table,
    print_rich_schema,
    print_rich_extent,
    print_rich_peek,
)
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


def _launch_tui(dataset_path=None):
    """Launch the TUI app. Separated for testability."""
    from geopeek.tui.app import run_tui

    run_tui(dataset_path=dataset_path)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        # No subcommand — launch TUI with file picker
        _launch_tui()
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


@app.command()
def peek(
    input_file: str = typer.Argument(..., help="Path to input file or directory."),
    format: OutputFormat = typer.Option(
        OutputFormat.table,
        "--format",
        "-f",
        help="Output format: table or json.",
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        help="Number of rows to preview.",
    ),
    layer: str = typer.Option(
        None,
        "--layer",
        "-l",
        help="Layer name (for multi-layer datasets).",
    ),
):
    """Preview data rows (vector) or band statistics (raster)."""
    handler = _select_handler(input_file)
    data = handler.peek(limit=limit, layer_name=layer)
    data_type = _type_label_for(input_file)

    if format == OutputFormat.json:
        print_json(data)
    else:
        print_rich_peek(data, f"{data_type} Preview")


@app.command()
def schema(
    input_file: str = typer.Argument(..., help="Path to input file or directory."),
    format: OutputFormat = typer.Option(
        OutputFormat.table,
        "--format",
        "-f",
        help="Output format: table or json.",
    ),
    layer: str = typer.Option(
        None,
        "--layer",
        "-l",
        help="Layer name (for multi-layer datasets).",
    ),
):
    """Show field schema (vector) or band schema (raster)."""
    handler = _select_handler(input_file)
    data = handler.get_schema(layer_name=layer)
    data_type = _type_label_for(input_file)

    if format == OutputFormat.json:
        print_json(data)
    else:
        print_rich_schema(data, f"{data_type} Schema")


@app.command()
def extent(
    input_file: str = typer.Argument(..., help="Path to input file or directory."),
    format: OutputFormat = typer.Option(
        OutputFormat.table,
        "--format",
        "-f",
        help="Output format: table or json.",
    ),
    layer: str = typer.Option(
        None,
        "--layer",
        "-l",
        help="Layer name (for multi-layer datasets).",
    ),
):
    """Show bounding box extent."""
    handler = _select_handler(input_file)
    data = handler.get_extent(layer_name=layer)
    data_type = _type_label_for(input_file)

    if format == OutputFormat.json:
        print_json(data)
    else:
        print_rich_extent(data, f"{data_type} Extent")


@app.command()
def browse(
    input_file: str = typer.Argument(
        ..., help="Path to dataset to browse interactively."
    ),
):
    """Launch interactive TUI to explore a dataset."""
    _launch_tui(dataset_path=input_file)


if __name__ == "__main__":
    app()
