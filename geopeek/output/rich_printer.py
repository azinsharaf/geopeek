from rich.table import Table
from rich.console import Console

def print_rich_table(metadata: dict, title: str):
    """Print metadata as a Rich table."""
    console = Console()
    table = Table(title=title)
    for key, value in metadata.items():
        table.add_row(key, str(value))
    console.print(table)
