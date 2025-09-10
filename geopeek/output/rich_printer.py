from rich.table import Table
from rich.console import Console

def print_rich_table(metadata: dict, title: str):
    """Print metadata as a Rich table."""
    console = Console()
    table = Table(title=title)
    for key, value in metadata.items():
        if isinstance(value, list):
            # If the value is a list, add each item as a row
            for item in value:
                table.add_row(key, str(item))
        else:
            table.add_row(key, str(value))
    console.print(table)
