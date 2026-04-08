"""Explorer panel — persistent file browser for geospatial datasets."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.message import Message
from textual.widgets import DirectoryTree, Static


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


class GeoFilteredTree(DirectoryTree):
    """DirectoryTree that only shows geospatial files and directories."""

    def filter_paths(self, paths: list[Path]) -> list[Path]:
        result = []
        for p in paths:
            if p.name.startswith("."):
                continue
            if p.is_dir():
                result.append(p)
            elif p.suffix.lower() in _ALL_EXTS:
                result.append(p)
        return result


class ExplorerPanel(Static):
    """Persistent file explorer panel with Bagels-style card design."""

    can_focus = False  # Focus goes to the tree inside

    class DatasetSelected(Message):
        """Posted when user selects a geospatial dataset."""

        def __init__(self, path: str) -> None:
            super().__init__()
            self.path = path

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
        """Handle directory selection — open .gdb directories as datasets."""
        if event.path.suffix.lower() == _GDB_EXT:
            event.stop()
            self.post_message(self.DatasetSelected(str(event.path)))
