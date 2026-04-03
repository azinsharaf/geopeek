from rich.table import Table
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


def _safe_str(val):
    """Convert a value to a display string, handling common types."""
    if val is None:
        return "-"
    if isinstance(val, bool):
        return str(val)
    if isinstance(val, dict):
        return ", ".join(f"{k}={v}" for k, v in val.items())
    if isinstance(val, list):
        if not val:
            return "-"
        # If list of dicts (layers, fields, bands), return count as summary
        if isinstance(val[0], dict):
            return f"{len(val)} items (see below)"
        return ", ".join(str(x) for x in val)
    if isinstance(val, float):
        return f"{val:.6f}" if abs(val) < 1 else f"{val:.2f}"
    return str(val)


def _format_extent(extent: dict) -> str:
    """Format an extent dict as a readable string."""
    if not extent:
        return "-"
    return (
        f"X: [{extent.get('xmin', '?'):.4f}, {extent.get('xmax', '?'):.4f}]  "
        f"Y: [{extent.get('ymin', '?'):.4f}, {extent.get('ymax', '?'):.4f}]"
    )


def _render_fields_table(fields: list) -> Table:
    """Render a list of field dicts as a Rich sub-table."""
    table = Table(show_header=True, show_lines=False, padding=(0, 1))
    table.add_column("Field Name", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Width", style="yellow", justify="right")
    for f in fields:
        table.add_row(f.get("name", "?"), f.get("type", "?"), str(f.get("width", "")))
    return table


def _render_bands_table(bands: list) -> Table:
    """Render a list of band dicts as a Rich sub-table."""
    table = Table(show_header=True, show_lines=False, padding=(0, 1))
    table.add_column("Band", justify="right")
    table.add_column("Data Type", style="green")
    table.add_column("NoData", style="yellow")
    table.add_column("Min", justify="right")
    table.add_column("Max", justify="right")
    table.add_column("Mean", justify="right")
    table.add_column("StdDev", justify="right")
    for b in bands:
        table.add_row(
            str(b.get("band", "?")),
            b.get("data_type", "?"),
            str(b.get("nodata", "-")),
            f"{b['min']:.2f}" if b.get("min") is not None else "-",
            f"{b['max']:.2f}" if b.get("max") is not None else "-",
            f"{b['mean']:.2f}" if b.get("mean") is not None else "-",
            f"{b['stddev']:.2f}" if b.get("stddev") is not None else "-",
        )
    return table


def _render_layer_panel(layer: dict, index: int) -> Panel:
    """Render a single layer dict as a Rich panel with a sub-table."""
    name = layer.get("name", f"Layer {index}")
    table = Table(show_header=False, show_lines=False, padding=(0, 1))
    table.add_column("Property", style="bold")
    table.add_column("Value")

    skip_keys = {"name", "fields", "extent"}
    for key, val in layer.items():
        if key in skip_keys:
            continue
        table.add_row(key, _safe_str(val))

    # Extent
    extent = layer.get("extent")
    if extent:
        table.add_row("extent", _format_extent(extent))

    # Fields sub-table
    fields = layer.get("fields", [])
    if fields:
        table.add_row("fields", f"{len(fields)} fields")

    return Panel(table, title=f"[bold cyan]{name}[/bold cyan]", border_style="dim")


def print_rich_table(metadata: dict, title: str):
    """Print metadata as a Rich table, with nested sub-tables for layers/bands."""
    console = Console()

    # Top-level properties table
    table = Table(title=title, show_header=False, show_lines=False, padding=(0, 1))
    table.add_column("Property", style="bold")
    table.add_column("Value")

    layers = None
    bands = None
    fields = None

    for key, val in metadata.items():
        if (
            key == "layers"
            and isinstance(val, list)
            and val
            and isinstance(val[0], dict)
        ):
            layers = val
            table.add_row(key, f"{len(val)} layers")
            continue
        if key == "bands" and isinstance(val, list):
            bands = val
            table.add_row(key, f"{len(val)} bands")
            continue
        if key == "fields" and isinstance(val, list):
            fields = val
            table.add_row(key, f"{len(val)} fields")
            continue
        if key == "extent" and isinstance(val, dict):
            table.add_row(key, _format_extent(val))
            continue
        table.add_row(key, _safe_str(val))

    console.print()  # blank line before output
    console.print(table)

    # Render top-level fields (e.g., single shapefile with flattened metadata)
    if fields:
        console.print(_render_fields_table(fields))

    # Render layer details
    if layers:
        for i, layer in enumerate(layers):
            console.print(_render_layer_panel(layer, i))
            # Show fields table for each layer
            layer_fields = layer.get("fields", [])
            if layer_fields:
                console.print(_render_fields_table(layer_fields))
                console.print()

    # Render band details for rasters
    if bands:
        console.print(_render_bands_table(bands))
