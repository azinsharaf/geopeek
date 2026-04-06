"""Geopeek TUI — interactive geospatial data explorer."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    DataTable,
    DirectoryTree,
    Footer,
    Header,
    Static,
    Tree,
)
from textual.widgets.tree import TreeNode


# Geospatial file extensions we recognize
_VECTOR_EXTS = {".shp"}
_RASTER_EXTS = {
    ".tif",
    ".tiff",
    ".img",
    ".vrt",
    ".jp2",
    ".png",
    ".jpg",
    ".jpeg",
    ".dem",
}
_GDB_EXT = ".gdb"

_ALL_EXTS = _VECTOR_EXTS | _RASTER_EXTS


def _is_geospatial(path: Path) -> bool:
    """Check if a path is a recognized geospatial file or directory."""
    if path.is_file() and path.suffix.lower() in _ALL_EXTS:
        return True
    if path.is_dir() and path.suffix.lower() == _GDB_EXT:
        return True
    return False


def _select_handler(path: str):
    """Select the right handler for a given path (same logic as cli.py)."""
    lower = path.lower()
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
        and any(n.lower().endswith(".gdb") for n in os.listdir(path))
    ):
        from geopeek.handlers.gdb_handler import GDBHandler

        return GDBHandler(path)
    return None


class GeoFilteredTree(DirectoryTree):
    """DirectoryTree that highlights geospatial files."""

    def filter_paths(self, paths: list[Path]) -> list[Path]:
        """Show directories and geospatial files only."""
        result = []
        for p in paths:
            if p.name.startswith("."):
                continue
            if p.is_dir():
                result.append(p)
            elif p.suffix.lower() in _ALL_EXTS:
                result.append(p)
        return result


class GeopeekApp(App):
    """The main Geopeek TUI application."""

    TITLE = "geopeek"
    CSS = """
    #file-picker {
        width: 100%;
        height: 100%;
    }

    #dataset-view {
        width: 100%;
        height: 100%;
    }

    #layer-tree-panel {
        width: 30;
        min-width: 20;
        height: 100%;
        border-right: solid $surface-lighten-2;
    }

    #layer-tree-title {
        height: 1;
        padding: 0 1;
        background: $accent;
        color: $text;
        text-style: bold;
    }

    #layer-tree {
        width: 100%;
        height: 1fr;
    }

    #right-panel {
        width: 1fr;
        height: 100%;
    }

    #metadata-panel {
        height: 1fr;
        min-height: 8;
        padding: 0 1;
        border-bottom: solid $surface-lighten-2;
        overflow-y: auto;
    }

    #metadata-title {
        height: 1;
        padding: 0 1;
        background: $accent;
        color: $text;
        text-style: bold;
    }

    #data-grid-panel {
        height: 2fr;
        min-height: 6;
    }

    #data-grid-title {
        height: 1;
        padding: 0 1;
        background: $accent;
        color: $text;
        text-style: bold;
    }

    #data-grid {
        height: 1fr;
    }

    #picker-title {
        height: 1;
        padding: 0 1;
        background: $accent;
        color: $text;
        text-style: bold;
    }

    #dir-tree {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("escape", "back", "Back", show=True),
        Binding("r", "refresh", "Refresh", show=True),
    ]

    def __init__(self, dataset_path: Optional[str] = None):
        super().__init__()
        self.dataset_path = dataset_path
        self._handler = None
        self._current_layer: Optional[str] = None
        self._is_raster = False

    def compose(self) -> ComposeResult:
        yield Header()
        if self.dataset_path:
            yield from self._compose_dataset_view()
        else:
            yield from self._compose_file_picker()
        yield Footer()

    def _compose_file_picker(self) -> ComposeResult:
        """Compose the file picker view."""
        with Vertical(id="file-picker"):
            yield Static("Select a geospatial dataset", id="picker-title")
            yield GeoFilteredTree(str(Path.cwd()), id="dir-tree")

    def _compose_dataset_view(self) -> ComposeResult:
        """Compose the dataset exploration view."""
        with Horizontal(id="dataset-view"):
            with Vertical(id="layer-tree-panel"):
                yield Static("Layers", id="layer-tree-title")
                yield Tree("Layers", id="layer-tree")
            with Vertical(id="right-panel"):
                with Vertical(id="metadata-panel"):
                    yield Static("Metadata", id="metadata-title")
                    yield Static("Loading...", id="metadata-content")
                with Vertical(id="data-grid-panel"):
                    yield Static("Data", id="data-grid-title")
                    yield DataTable(id="data-grid")

    def on_mount(self) -> None:
        if self.dataset_path:
            self._load_dataset(self.dataset_path)

    @on(DirectoryTree.FileSelected, "#dir-tree")
    def on_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Handle file selection in the file picker."""
        path = event.path
        if _is_geospatial(path):
            self._open_dataset(str(path))

    @on(DirectoryTree.DirectorySelected, "#dir-tree")
    def on_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        """Handle directory selection — open .gdb directories directly."""
        path = event.path
        if path.suffix.lower() == _GDB_EXT:
            event.stop()
            self._open_dataset(str(path))

    def _open_dataset(self, path: str) -> None:
        """Switch from file picker to dataset view."""
        self.dataset_path = path
        # Remove file picker, mount dataset view
        file_picker = self.query_one("#file-picker")
        file_picker.remove()
        # Build dataset view widgets
        container = Horizontal(id="dataset-view")
        layer_panel = Vertical(id="layer-tree-panel")
        right_panel = Vertical(id="right-panel")
        meta_panel = Vertical(id="metadata-panel")
        grid_panel = Vertical(id="data-grid-panel")

        self.mount(container, before=self.query_one(Footer))

        container.mount(layer_panel)
        container.mount(right_panel)

        layer_panel.mount(Static("Layers", id="layer-tree-title"))
        layer_panel.mount(Tree("Layers", id="layer-tree"))

        right_panel.mount(meta_panel)
        right_panel.mount(grid_panel)

        meta_panel.mount(Static("Metadata", id="metadata-title"))
        meta_panel.mount(Static("Loading...", id="metadata-content"))

        grid_panel.mount(Static("Data", id="data-grid-title"))
        grid_panel.mount(DataTable(id="data-grid"))

        self._load_dataset(path)

    @work(thread=True)
    def _load_dataset(self, path: str) -> None:
        """Load dataset in a background thread."""
        handler = _select_handler(path)
        if handler is None:
            self.call_from_thread(self._show_error, f"Unsupported dataset: {path}")
            return

        self._handler = handler
        self._is_raster = path.lower().endswith(
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
        )

        # Get layers
        layers = handler.get_layers()
        # Get top-level info
        info = handler.get_info()

        self.call_from_thread(self._populate_layers, layers, info, path)

    def _show_error(self, message: str) -> None:
        """Show an error in the metadata panel."""
        try:
            content = self.query_one("#metadata-content", Static)
            content.update(f"[red]{message}[/red]")
        except Exception:
            pass

    def _populate_layers(self, layers: list[str], info: dict, path: str) -> None:
        """Populate the layer tree and metadata panel."""
        self.sub_title = Path(path).name

        # Populate layer tree
        try:
            tree = self.query_one("#layer-tree", Tree)
            tree.clear()
            tree.root.set_label(Path(path).name)

            if layers:
                for layer_name in layers:
                    tree.root.add_leaf(layer_name, data=layer_name)
                tree.root.expand()
            else:
                tree.root.add_leaf("(no layers)", data=None)
                tree.root.expand()
        except Exception:
            pass

        # Populate metadata
        self._show_metadata(info)

        # If single layer or raster, auto-load data
        if layers and not self._is_raster:
            self._current_layer = layers[0]
            self._load_peek_data(layers[0])
        elif self._is_raster:
            self._show_data_grid_message(
                "Raster dataset — no attribute rows to display."
            )

    @on(Tree.NodeSelected, "#layer-tree")
    def on_layer_selected(self, event: Tree.NodeSelected) -> None:
        """Handle layer selection in the layer tree."""
        layer_name = event.node.data
        if layer_name is None:
            return
        self._current_layer = layer_name
        self._load_layer_info(layer_name)

    @work(thread=True)
    def _load_layer_info(self, layer_name: str) -> None:
        """Load info for a selected layer in background."""
        if self._handler is None:
            return

        # Get schema for the layer
        schema = self._handler.get_schema(layer_name=layer_name)
        extent = self._handler.get_extent(layer_name=layer_name)

        # Build metadata dict
        meta = {}
        if "error" not in schema:
            meta["layer"] = schema.get("layer", layer_name)
            meta["geometry_type"] = schema.get("geometry_type", "-")
            meta["field_count"] = schema.get("field_count", 0)
        if "error" not in extent:
            meta["crs"] = extent.get("crs", "-")
            ext = extent.get("extent")
            if ext:
                meta["extent"] = (
                    f"X: [{ext['xmin']:.4f}, {ext['xmax']:.4f}]  "
                    f"Y: [{ext['ymin']:.4f}, {ext['ymax']:.4f}]"
                )
        if schema.get("fields"):
            fields_summary = ", ".join(
                f"{f['name']} ({f['type']})" for f in schema["fields"][:10]
            )
            if len(schema["fields"]) > 10:
                fields_summary += f"  ... and {len(schema['fields']) - 10} more"
            meta["fields"] = fields_summary

        self.call_from_thread(self._show_metadata, meta)

        # Load peek data
        if not self._is_raster:
            peek_data = self._handler.peek(limit=50, layer_name=layer_name)
            self.call_from_thread(self._show_peek_data, peek_data)

    def _show_metadata(self, info: dict) -> None:
        """Update the metadata panel with info dict."""
        try:
            content = self.query_one("#metadata-content", Static)
            lines = []
            for key, val in info.items():
                if (
                    key in ("layers", "fields")
                    and isinstance(val, list)
                    and val
                    and isinstance(val[0], dict)
                ):
                    lines.append(f"[bold]{key}:[/bold] {len(val)} items")
                    continue
                if key == "bands" and isinstance(val, list):
                    lines.append(f"[bold]{key}:[/bold] {len(val)} bands")
                    continue
                if key == "extent" and isinstance(val, dict):
                    ext = val
                    lines.append(
                        f"[bold]extent:[/bold] X: [{ext.get('xmin', '?'):.4f}, {ext.get('xmax', '?'):.4f}]  "
                        f"Y: [{ext.get('ymin', '?'):.4f}, {ext.get('ymax', '?'):.4f}]"
                    )
                    continue
                lines.append(f"[bold]{key}:[/bold] {val}")
            content.update("\n".join(lines) if lines else "No metadata available.")
        except Exception:
            pass

    @work(thread=True)
    def _load_peek_data(self, layer_name: str) -> None:
        """Load peek data in background."""
        if self._handler is None:
            return
        peek_data = self._handler.peek(limit=50, layer_name=layer_name)
        self.call_from_thread(self._show_peek_data, peek_data)

    def _show_peek_data(self, peek_data: dict) -> None:
        """Populate the data grid with peek results."""
        try:
            grid = self.query_one("#data-grid", DataTable)
            grid.clear(columns=True)

            if "error" in peek_data:
                self._show_data_grid_message(peek_data["error"])
                return

            columns = peek_data.get("columns", [])
            rows = peek_data.get("rows", [])
            total = peek_data.get("total_features", "?")
            showing = peek_data.get("showing", 0)

            # Update title
            title = self.query_one("#data-grid-title", Static)
            title.update(f"Data — {showing} of {total} features")

            if not columns or not rows:
                return

            # Add columns
            for col in columns:
                grid.add_column(col, key=col)

            # Add rows
            for row in rows:
                grid.add_row(*[str(row.get(col, "")) for col in columns])

        except Exception:
            pass

    def _show_data_grid_message(self, message: str) -> None:
        """Show a message in the data grid area."""
        try:
            title = self.query_one("#data-grid-title", Static)
            title.update(f"Data — {message}")
        except Exception:
            pass

    def action_back(self) -> None:
        """Go back to file picker from dataset view."""
        if self.dataset_path and self.query("#file-picker"):
            return  # already on file picker
        if self.dataset_path:
            # Remove dataset view, show file picker
            try:
                dv = self.query_one("#dataset-view")
                dv.remove()
            except Exception:
                pass
            self.dataset_path = None
            self._handler = None
            self._current_layer = None
            self.sub_title = ""

            container = Vertical(id="file-picker")
            self.mount(container, before=self.query_one(Footer))
            container.mount(Static("Select a geospatial dataset", id="picker-title"))
            container.mount(GeoFilteredTree(str(Path.cwd()), id="dir-tree"))

    def action_refresh(self) -> None:
        """Reload the current dataset."""
        if self.dataset_path:
            self._load_dataset(self.dataset_path)


def run_tui(dataset_path: Optional[str] = None) -> None:
    """Entry point to launch the TUI."""
    app = GeopeekApp(dataset_path=dataset_path)
    app.run()
