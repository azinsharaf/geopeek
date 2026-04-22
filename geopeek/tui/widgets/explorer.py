"""Explorer panel — persistent file browser for geospatial datasets."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from textual import work
from textual.app import ComposeResult
from textual.message import Message
from textual.widgets import DirectoryTree, Static, Tree
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


def is_geospatial(path: Path) -> bool:
    """Check if a path is a recognized geospatial file or directory."""
    if path.is_file() and path.suffix.lower() in _ALL_EXTS:
        return True
    if path.is_dir() and path.suffix.lower() == _GDB_EXT:
        return True
    return False


def _is_inside_gdb(path: Path) -> bool:
    """Check if a path is inside a .gdb directory."""
    for parent in path.parents:
        if parent.suffix.lower() == _GDB_EXT:
            return True
    return False


class GeoFilteredTree(DirectoryTree):
    """DirectoryTree that shows geospatial files and directories.

    .gdb directories are shown but their internal files are hidden.
    Instead, layers are populated as virtual leaf nodes when expanded.
    """

    # Track which .gdb nodes have been populated with layers
    _gdb_populated: set[str]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._gdb_populated = set()

    def filter_paths(self, paths: list[Path]) -> list[Path]:
        result = []
        for p in paths:
            if p.name.startswith("."):
                continue
            # Hide internal .gdb files — layers are added as virtual nodes
            if _is_inside_gdb(p):
                continue
            if p.is_dir():
                result.append(p)
            elif p.suffix.lower() in _ALL_EXTS:
                result.append(p)
        return result

    async def _on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Override to skip virtual layer nodes (dict data) that would crash
        the parent DirectoryTree handler expecting DirEntry objects."""
        if isinstance(event.node.data, dict):
            # This is a virtual layer node — don't let DirectoryTree handle it.
            # prevent_default() stops the MRO walk so DirectoryTree._on_tree_node_selected
            # is never called (it would crash doing dir_entry.path on a dict).
            # Without calling event.stop(), the event still bubbles up to
            # ExplorerPanel.on_tree_node_selected which handles it correctly.
            event.prevent_default()
            return
        await super()._on_tree_node_selected(event)


class ExplorerPanel(Static):
    """Persistent file explorer panel with Bagels-style card design."""

    can_focus = False  # Focus goes to the tree inside

    class DatasetSelected(Message):
        """Posted when user selects a geospatial dataset."""

        def __init__(self, path: str, layer_name: Optional[str] = None) -> None:
            super().__init__()
            self.path = path
            self.layer_name = layer_name

    def __init__(self, start_path: str | None = None) -> None:
        super().__init__(id="explorer-panel", classes="module-container")
        self._start_path = start_path or str(Path.cwd())
        self.border_title = "Explorer"
        self.border_subtitle = "enter"

    def compose(self) -> ComposeResult:
        yield GeoFilteredTree(self._start_path, id="dir-tree")

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        """Handle file selection — post DatasetSelected if geospatial."""
        if is_geospatial(event.path):
            event.stop()
            self.post_message(self.DatasetSelected(str(event.path)))

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        """Handle .gdb directory selection — expand to show layers."""
        if event.path.suffix.lower() == _GDB_EXT:
            event.stop()
            tree = self.query_one("#dir-tree", GeoFilteredTree)
            node = event.node
            gdb_path = str(event.path)

            # If already populated with layers, just toggle expand
            if gdb_path in tree._gdb_populated:
                node.toggle()
                return

            # Populate layers from the GDB handler
            self._populate_gdb_layers(node, gdb_path)

    @work(thread=True)
    def _populate_gdb_layers(self, node: TreeNode, gdb_path: str) -> None:
        """Load GDB layers in a background thread and add as children."""
        try:
            from geopeek.handlers.gdb_handler import GDBHandler

            handler = GDBHandler(gdb_path)
            layers = handler.get_layers()
        except Exception:
            layers = []

        self.app.call_from_thread(self._add_layer_nodes, node, gdb_path, layers)

    def _add_layer_nodes(
        self, node: TreeNode, gdb_path: str, layers: list[str]
    ) -> None:
        """Add layer names as leaf nodes under the .gdb node."""
        tree = self.query_one("#dir-tree", GeoFilteredTree)

        # Remove any existing children (filesystem entries filtered to empty)
        node.remove_children()

        if layers:
            for layer_name in sorted(layers):
                # Store both gdb_path and layer_name in the node data
                node.add_leaf(
                    f"  {layer_name}",
                    data={"gdb_path": gdb_path, "layer_name": layer_name},
                )
        else:
            node.add_leaf("  (no layers)", data=None)

        tree._gdb_populated.add(gdb_path)
        node.expand()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle selection of a layer node inside a .gdb."""
        data = event.node.data
        if isinstance(data, dict) and "gdb_path" in data:
            event.stop()
            self.post_message(
                self.DatasetSelected(
                    path=data["gdb_path"],
                    layer_name=data["layer_name"],
                )
            )
