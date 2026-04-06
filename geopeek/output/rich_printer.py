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


def print_rich_schema(data: dict, title: str):
    """Print schema information as Rich tables."""
    console = Console()

    if "error" in data:
        console.print(f"[red]{data['error']}[/red]")
        return

    # Multi-layer schema (GDB with no --layer specified)
    if "schemas" in data:
        console.print()
        console.print(f"[bold]{title}[/bold] ({data.get('layer_count', '?')} layers)")
        for schema in data["schemas"]:
            _print_single_schema(console, schema)
        return

    # Single layer schema
    console.print()
    _print_single_schema(console, data)


def _print_single_schema(console: Console, schema: dict):
    """Print schema for a single layer."""
    layer_name = schema.get("layer", "Unknown")
    geom_type = schema.get("geometry_type", "-")
    field_count = schema.get("field_count", 0)

    # For rasters, show band schema
    if "bands" in schema:
        console.print(
            f"\n[bold cyan]{schema.get('path', 'Raster')}[/bold cyan]"
            f"  Driver: {schema.get('driver', '-')}"
            f"  Size: {schema.get('columns', '?')}x{schema.get('rows', '?')}"
            f"  Bands: {schema.get('band_count', '?')}"
        )
        table = Table(show_header=True, show_lines=False, padding=(0, 1))
        table.add_column("Band", justify="right")
        table.add_column("Data Type", style="green")
        table.add_column("NoData", style="yellow")
        table.add_column("Color Interp", style="cyan")
        table.add_column("Block Size")
        for b in schema["bands"]:
            table.add_row(
                str(b.get("band", "?")),
                b.get("data_type", "?"),
                str(b.get("nodata", "-")),
                b.get("color_interp", "-"),
                b.get("block_size", "-"),
            )
        console.print(table)
        return

    # Vector schema
    console.print(
        f"\n[bold cyan]{layer_name}[/bold cyan]"
        f"  Geometry: {geom_type}  Fields: {field_count}"
    )
    fields = schema.get("fields", [])
    if fields:
        table = Table(show_header=True, show_lines=False, padding=(0, 1))
        table.add_column("Field Name", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Width", style="yellow", justify="right")
        table.add_column("Precision", style="dim", justify="right")
        for f in fields:
            table.add_row(
                f.get("name", "?"),
                f.get("type", "?"),
                str(f.get("width", "")),
                str(f.get("precision", "")),
            )
        console.print(table)


def print_rich_extent(data: dict, title: str):
    """Print extent information as a Rich table."""
    console = Console()

    if "error" in data:
        console.print(f"[red]{data['error']}[/red]")
        return

    # Multi-layer extents (GDB with no --layer specified)
    if "extents" in data:
        console.print()
        console.print(f"[bold]{title}[/bold] ({data.get('layer_count', '?')} layers)")
        table = Table(show_header=True, show_lines=True, padding=(0, 1))
        table.add_column("Layer", style="cyan")
        table.add_column("CRS", style="green")
        table.add_column("Extent")
        for entry in data["extents"]:
            ext = entry.get("extent")
            table.add_row(
                entry.get("layer", "?"),
                entry.get("crs", "-") or "-",
                _format_extent(ext) if ext else "-",
            )
        console.print(table)
        return

    # Single extent
    console.print()
    table = Table(title=title, show_header=False, show_lines=False, padding=(0, 1))
    table.add_column("Property", style="bold")
    table.add_column("Value")

    for key, val in data.items():
        if key == "extent" and isinstance(val, dict):
            table.add_row("xmin", f"{val.get('xmin', '?'):.6f}")
            table.add_row("xmax", f"{val.get('xmax', '?'):.6f}")
            table.add_row("ymin", f"{val.get('ymin', '?'):.6f}")
            table.add_row("ymax", f"{val.get('ymax', '?'):.6f}")
            continue
        table.add_row(key, _safe_str(val))

    console.print(table)


def print_rich_peek(data: dict, title: str):
    """Print data preview as a Rich table (attribute rows or band stats)."""
    console = Console()

    if "error" in data:
        console.print(f"[red]{data['error']}[/red]")
        return

    # Raster peek — band statistics
    if "bands" in data and "rows" not in data:
        console.print()
        note = data.get("note", "")
        if note:
            console.print(f"[dim]{note}[/dim]")
        console.print(
            f"[bold]{title}[/bold]"
            f"  Size: {data.get('columns', '?')}x{data.get('rows', '?')}"
            f"  Bands: {data.get('band_count', '?')}"
        )
        table = Table(show_header=True, show_lines=False, padding=(0, 1))
        table.add_column("Band", justify="right")
        table.add_column("Data Type", style="green")
        table.add_column("NoData", style="yellow")
        table.add_column("Min", justify="right")
        table.add_column("Max", justify="right")
        table.add_column("Mean", justify="right")
        table.add_column("StdDev", justify="right")
        table.add_column("Color", style="cyan")
        for b in data["bands"]:
            table.add_row(
                str(b.get("band", "?")),
                b.get("data_type", "?"),
                str(b.get("nodata", "-")),
                f"{b['min']:.2f}" if b.get("min") is not None else "-",
                f"{b['max']:.2f}" if b.get("max") is not None else "-",
                f"{b['mean']:.2f}" if b.get("mean") is not None else "-",
                f"{b['stddev']:.2f}" if b.get("stddev") is not None else "-",
                b.get("color_interp", "-"),
            )
        console.print(table)
        return

    # Vector peek — attribute rows
    console.print()
    layer = data.get("layer", "Data")
    total = data.get("total_features", "?")
    showing = data.get("showing", 0)
    console.print(
        f"[bold]{title}[/bold]  Layer: [cyan]{layer}[/cyan]"
        f"  Showing {showing} of {total} features"
    )

    columns = data.get("columns", [])
    rows = data.get("rows", [])

    if not rows:
        console.print("[dim]No features to display.[/dim]")
        return

    table = Table(show_header=True, show_lines=True, padding=(0, 1))
    for col in columns:
        if col == "FID":
            table.add_column(col, justify="right", style="dim")
        elif col == "geometry":
            table.add_column(col, style="cyan")
        else:
            table.add_column(col)

    for row in rows:
        table.add_row(*[_safe_str(row.get(col)) for col in columns])

    console.print(table)
