from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import DataTable, Tree
import fiona

class GDBBrowser(App):
    CSS = "Screen { layout: horizontal; }"

    def __init__(self, path: str):
        super().__init__()
        self.path = path

    def compose(self) -> ComposeResult:
        yield Tree("Feature Classes", id="layers")
        yield DataTable(id="details")

    def on_mount(self) -> None:
        tree = self.query_one("#layers", Tree)
        with fiona.Env():
            with fiona.open(self.path) as src:
                for layer in src.session.files:
                    tree.root.add(layer)
        tree.root.expand()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        layer = event.node.label
        table = self.query_one("#details", DataTable)
        table.clear()
        try:
            with fiona.open(self.path, layer=layer) as lyr:
                table.add_column("Field")
                table.add_column("Type")
                for name, field in lyr.schema["properties"].items():
                    table.add_row(name, str(field))
        except Exception as e:
            table.add_row("Error", str(e))

def browse_app(path: str):
    """Launch the TUI for browsing a GIS dataset."""
    app = GDBBrowser(path)
    app.run()

if __name__ == "__main__":
    import sys
    browse_app(sys.argv[1])
