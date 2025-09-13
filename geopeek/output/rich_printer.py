from rich.table import Table
from rich.console import Console

def _safe_str(val):
    if isinstance(val, list):
        return ", ".join(str(x) for x in val) if val else ""
    return str(val)

def print_rich_table(metadata: dict, title: str):
    """Print metadata as a Rich table with safe string conversion."""
    console = Console()
    table = Table(title=title)
    for key, value in metadata.items():
        table.add_row(key, _safe_str(value))
    console.print(table)
