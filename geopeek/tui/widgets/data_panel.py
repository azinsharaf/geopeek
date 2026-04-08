"""Data panel — displays attribute table and metadata for a dataset."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Static


class MetadataPanel(Static):
    """Compact horizontal metadata summary — its own bordered card."""

    can_focus = False

    def __init__(self) -> None:
        super().__init__(id="metadata-panel", classes="module-container")
        self.border_title = "Metadata"

    def compose(self) -> ComposeResult:
        yield Static("No dataset loaded.", id="metadata-content")

    # Keys displayed on line 1 (quick-glance overview)
    _LINE1_KEYS = {"type", "crs", "feature_count", "geometry_type", "size", "driver"}
    # Keys displayed on line 2 (spatial details)
    _LINE2_KEYS = {"extent", "layers", "fields", "bands"}
    # Keys to skip entirely (already shown elsewhere or too verbose)
    _SKIP_KEYS = {"path"}

    # Rich markup color for metadata keys
    _KEY_COLOR = "#94e2d5"  # Catppuccin teal

    def set_metadata(self, info: dict) -> None:
        """Format and display metadata as two lines with colored keys."""
        try:
            content = self.query_one("#metadata-content", Static)
            line1_parts = []
            line2_parts = []

            for key, val in info.items():
                if key in self._SKIP_KEYS:
                    continue

                # Format the value based on type
                if key == "extent" and isinstance(val, dict):
                    formatted = (
                        f"X:[{val.get('xmin', '?'):.4f}, {val.get('xmax', '?'):.4f}]  "
                        f"Y:[{val.get('ymin', '?'):.4f}, {val.get('ymax', '?'):.4f}]"
                    )
                elif (
                    key in ("layers", "fields")
                    and isinstance(val, list)
                    and val
                    and isinstance(val[0], dict)
                ):
                    formatted = str(len(val))
                elif key == "bands" and isinstance(val, list):
                    formatted = f"{len(val)} bands"
                else:
                    formatted = str(val)

                entry = f"[bold {self._KEY_COLOR}]{key}:[/]  {formatted}"

                if key in self._LINE1_KEYS:
                    line1_parts.append(entry)
                elif key in self._LINE2_KEYS:
                    line2_parts.append(entry)
                else:
                    # Unknown keys go to line 1
                    line1_parts.append(entry)

            lines = []
            if line1_parts:
                lines.append("    ".join(line1_parts))
            if line2_parts:
                lines.append("    ".join(line2_parts))
            content.update("\n".join(lines) if lines else "No metadata available.")
        except Exception:
            pass

    def set_error(self, message: str) -> None:
        """Show an error message."""
        try:
            content = self.query_one("#metadata-content", Static)
            content.update(f"[bold red]{message}[/bold red]")
        except Exception:
            pass

    def clear(self) -> None:
        """Reset to empty state."""
        try:
            content = self.query_one("#metadata-content", Static)
            content.update("No dataset loaded.")
        except Exception:
            pass


class GridPanel(Static):
    """Attribute data grid — its own bordered card."""

    can_focus = False  # Focus goes to the DataTable inside

    def __init__(self) -> None:
        super().__init__(id="grid-panel", classes="module-container")
        self.border_title = "Data"
        self.border_subtitle = ""

    def compose(self) -> ComposeResult:
        yield DataTable(id="data-grid")

    def on_mount(self) -> None:
        grid = self.query_one("#data-grid", DataTable)
        grid.cursor_type = "row"


class DataPanel(Static):
    """Container for the Attributes tab content.

    Layout:
      MetadataPanel (2-line bordered card)
      GridPanel (data table, fills remaining space)
    """

    can_focus = False

    def __init__(self) -> None:
        super().__init__(id="data-panel")
        self._handler = None
        self._current_layer: Optional[str] = None
        self._is_raster = False
        self._dataset_path: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield MetadataPanel()
        yield GridPanel()

    def load_dataset(self, path: str) -> None:
        """Load a dataset and display its data."""
        self._dataset_path = path
        self._load_dataset(path)

    def clear_dataset(self) -> None:
        """Clear the current dataset display."""
        self._handler = None
        self._current_layer = None
        self._dataset_path = None
        try:
            self.query_one(MetadataPanel).clear()
            grid = self.query_one("#data-grid", DataTable)
            grid.clear(columns=True)
            self.query_one(GridPanel).border_title = "Data"
            self.query_one(GridPanel).border_subtitle = ""
        except Exception:
            pass

    def rebuild(self) -> None:
        """Refresh current dataset."""
        if self._dataset_path:
            self._load_dataset(self._dataset_path)

    @work(thread=True)
    def _load_dataset(self, path: str) -> None:
        """Load dataset in a background thread."""
        handler = self._select_handler(path)
        if handler is None:
            self.app.call_from_thread(
                self.query_one(MetadataPanel).set_error,
                f"Unsupported: {path}",
            )
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

        info = handler.get_info()
        layers = handler.get_layers()

        self.app.call_from_thread(self._populate, info, layers, path)

    def _populate(self, info: dict, layers: list[str], path: str) -> None:
        """Populate metadata and data grid."""
        self.query_one(MetadataPanel).set_metadata(info)

        if layers and not self._is_raster:
            self._current_layer = layers[0]
            self._load_peek_data(layers[0])
        elif self._is_raster:
            self._show_raster_info(info)

    def _show_raster_info(self, info: dict) -> None:
        """Show raster-specific info in the grid area."""
        try:
            grid = self.query_one("#data-grid", DataTable)
            grid.clear(columns=True)
            grid_panel = self.query_one(GridPanel)

            bands = info.get("bands", [])
            if bands:
                grid.add_column("Band", key="band")
                grid.add_column("Type", key="type")
                grid.add_column("NoData", key="nodata")
                grid.add_column("Min", key="min")
                grid.add_column("Max", key="max")
                for band in bands:
                    grid.add_row(
                        str(band.get("band", "")),
                        str(band.get("type", "")),
                        str(band.get("nodata", "")),
                        str(band.get("min", "")),
                        str(band.get("max", "")),
                    )
                grid_panel.border_title = "Bands"
                grid_panel.border_subtitle = f"{len(bands)} bands"
            else:
                grid_panel.border_title = "Data"
                grid_panel.border_subtitle = "raster"
        except Exception:
            pass

    @work(thread=True)
    def _load_peek_data(self, layer_name: str) -> None:
        """Load peek data in background."""
        if self._handler is None:
            return
        peek_data = self._handler.peek(limit=50, layer_name=layer_name)
        self.app.call_from_thread(self._show_peek_data, peek_data)

    def _show_peek_data(self, peek_data: dict) -> None:
        """Populate the data grid with peek results."""
        try:
            grid = self.query_one("#data-grid", DataTable)
            grid.clear(columns=True)
            grid_panel = self.query_one(GridPanel)

            if "error" in peek_data:
                self.query_one(MetadataPanel).set_error(peek_data["error"])
                return

            columns = peek_data.get("columns", [])
            rows = peek_data.get("rows", [])
            total = peek_data.get("total_features", "?")
            showing = peek_data.get("showing", 0)

            grid_panel.border_title = "Data"
            grid_panel.border_subtitle = f"{showing} of {total} features"

            if not columns or not rows:
                return

            for col in columns:
                grid.add_column(col, key=col)

            for row in rows:
                grid.add_row(*[str(row.get(col, "")) for col in columns])

        except Exception:
            pass

    @staticmethod
    def _select_handler(path: str):
        """Select the right handler for a given path."""
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
