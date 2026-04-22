"""Explorer panel — persistent file browser for geospatial datasets."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from textual import events, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widgets import DirectoryTree, Static, Tree
from textual.widgets.tree import TreeNode

from geopeek.tui.widgets.vim_table import SearchInput


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

    Vim key bindings:
      j / k          — cursor down / up
      l              — expand node (or enter first child if already expanded)
      h              — collapse node (or move to parent if already collapsed)
      g,g            — jump to top
      G              — jump to bottom
      ctrl+d         — half-page down
      ctrl+u         — half-page up
      z,z            — centre cursor in viewport
      /              — open inline search bar
      n / N          — next / previous search match
    """

    class SearchRequested(Message):
        """Posted when / is pressed; ExplorerPanel shows the search bar."""

    # Track which .gdb nodes have been populated with layers
    _gdb_populated: set[str]

    BINDINGS = [
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
        Binding("l", "vim_expand", show=False),
        Binding("h", "vim_collapse", show=False),
        Binding("g,g", "scroll_home", show=False),
        Binding("G", "scroll_end", show=False),
        Binding("ctrl+d", "vim_half_down", show=False),
        Binding("ctrl+u", "vim_half_up", show=False),
        Binding("z,z", "vim_center", show=False),
        Binding("/", "vim_search", show=False),
        Binding("n", "vim_search_next", show=False),
        Binding("N", "vim_search_prev", show=False),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._gdb_populated = set()
        self._search_matches: list[TreeNode] = []
        self._search_idx: int = -1

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

    # ------------------------------------------------------------------
    # Vim actions
    # ------------------------------------------------------------------

    def action_vim_expand(self) -> None:
        """l — expand node, or enter first child if already expanded."""
        node = self.cursor_node
        if node is None:
            return
        if not node.is_expanded and node.children:
            node.expand()
        elif node.is_expanded and node.children:
            self.move_cursor(node.children[0])
        else:
            # Leaf node — trigger selection (e.g. load a GDB layer)
            self.action_select_cursor()

    def action_vim_collapse(self) -> None:
        """h — collapse node, or move cursor to parent if already collapsed."""
        node = self.cursor_node
        if node is None:
            return
        if node.is_expanded:
            node.collapse()
        elif node.parent is not None and node.parent != self.root:
            self.move_cursor(node.parent)

    def action_vim_half_down(self) -> None:
        """ctrl+d — move cursor down by half the visible height."""
        half = max(1, self.size.height // 2)
        for _ in range(half):
            self.action_cursor_down()

    def action_vim_half_up(self) -> None:
        """ctrl+u — move cursor up by half the visible height."""
        half = max(1, self.size.height // 2)
        for _ in range(half):
            self.action_cursor_up()

    def action_vim_center(self) -> None:
        """z,z — scroll so the cursor line is centred in the viewport."""
        center_y = max(0, self.cursor_line - self.size.height // 2)
        self.scroll_to(y=center_y, animate=False)

    def action_vim_search(self) -> None:
        """/ — ask ExplorerPanel to show the search bar."""
        self.post_message(self.SearchRequested())

    def action_vim_search_next(self) -> None:
        """n — jump to the next search match."""
        if not self._search_matches:
            return
        self._search_idx = (self._search_idx + 1) % len(self._search_matches)
        self.move_cursor(self._search_matches[self._search_idx])

    def action_vim_search_prev(self) -> None:
        """N — jump to the previous search match."""
        if not self._search_matches:
            return
        self._search_idx = (self._search_idx - 1) % len(self._search_matches)
        self.move_cursor(self._search_matches[self._search_idx])

    # ------------------------------------------------------------------
    # Search logic
    # ------------------------------------------------------------------

    def jump_to_search(self, query: str) -> None:
        """Collect all nodes whose label contains *query* and jump to first."""
        self._search_matches = []
        self._search_idx = -1
        if not query:
            return
        q = query.lower()
        for node in self._iter_all_nodes(self.root):
            if q in str(node.label).strip().lower():
                self._search_matches.append(node)
        if self._search_matches:
            self._search_idx = 0
            self.move_cursor(self._search_matches[0])

    def _iter_all_nodes(self, node: TreeNode) -> list[TreeNode]:
        """Recursively collect every descendant of *node*."""
        result: list[TreeNode] = []
        for child in node.children:
            result.append(child)
            result.extend(self._iter_all_nodes(child))
        return result

    # ------------------------------------------------------------------
    # Internal overrides
    # ------------------------------------------------------------------

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
        search = SearchInput(placeholder="/  search tree...", id="tree-search")
        search.display = False
        yield search

    # ------------------------------------------------------------------
    # Tree search — triggered by GeoFilteredTree.SearchRequested
    # ------------------------------------------------------------------

    def on_geo_filtered_tree_search_requested(
        self, event: GeoFilteredTree.SearchRequested
    ) -> None:
        event.stop()
        search = self.query_one("#tree-search", SearchInput)
        search.display = True
        search.value = ""
        search.focus()

    def on_input_changed(self, event: SearchInput.Changed) -> None:
        if event.input.id == "tree-search":
            self.query_one("#dir-tree", GeoFilteredTree).jump_to_search(event.value)

    def on_input_submitted(self, event: SearchInput.Submitted) -> None:
        if event.input.id == "tree-search":
            self._hide_tree_search()

    def on_search_input_dismissed(self, event: SearchInput.Dismissed) -> None:
        self._hide_tree_search()

    def _hide_tree_search(self) -> None:
        search = self.query_one("#tree-search", SearchInput)
        search.display = False
        self.query_one("#dir-tree", GeoFilteredTree).focus()

    # ------------------------------------------------------------------
    # File / directory selection
    # ------------------------------------------------------------------

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
