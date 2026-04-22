"""Data panel — displays attribute table and metadata for a dataset."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Static

# How many rows to render immediately (fast first paint)
_INITIAL_ROWS = 200
# Rows appended per background chunk
_CHUNK_SIZE = 500

from geopeek.tui.widgets.vim_table import SearchInput, VimDataTable


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

    can_focus = False  # Focus goes to the VimDataTable inside

    def __init__(self) -> None:
        super().__init__(id="grid-panel", classes="module-container")
        self.border_title = "Data"
        self.border_subtitle = ""

    def compose(self) -> ComposeResult:
        yield VimDataTable(id="data-grid")
        search = SearchInput(placeholder="/  search rows...", id="grid-search")
        search.display = False
        yield search

    def on_mount(self) -> None:
        grid = self.query_one("#data-grid", VimDataTable)
        grid.cursor_type = "row"

    # ------------------------------------------------------------------
    # Grid search — triggered by VimDataTable.SearchRequested
    # ------------------------------------------------------------------

    def on_vim_data_table_search_requested(
        self, event: VimDataTable.SearchRequested
    ) -> None:
        event.stop()
        search = self.query_one("#grid-search", SearchInput)
        search.display = True
        search.value = ""
        search.focus()

    def on_input_changed(self, event: SearchInput.Changed) -> None:
        if event.input.id == "grid-search":
            self.query_one("#data-grid", VimDataTable).jump_to_search(event.value)

    def on_input_submitted(self, event: SearchInput.Submitted) -> None:
        if event.input.id == "grid-search":
            self._hide_grid_search()

    def on_search_input_dismissed(self, event: SearchInput.Dismissed) -> None:
        self._hide_grid_search()

    def _hide_grid_search(self) -> None:
        search = self.query_one("#grid-search", SearchInput)
        search.display = False
        self.query_one("#data-grid", VimDataTable).focus()


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
        self._requested_layer: Optional[str] = None
        self._is_raster = False
        self._dataset_path: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield MetadataPanel()
        yield GridPanel()

    def load_dataset(self, path: str, layer_name: Optional[str] = None) -> None:
        """Load a dataset and display its data.

        Args:
            path: Path to the dataset.
            layer_name: Optional layer name (for multi-layer datasets like .gdb).
        """
        self._dataset_path = path
        self._requested_layer = layer_name
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

        # For a specific layer, enrich info with layer-level details
        target_layer = self._requested_layer
        if target_layer and target_layer in layers:
            try:
                schema = handler.get_schema(layer_name=target_layer)
                extent = handler.get_extent(layer_name=target_layer)
                layer_info = {"layer": target_layer}
                if "error" not in schema:
                    layer_info["geometry_type"] = schema.get("geometry_type", "-")
                    layer_info["fields"] = schema.get("fields", [])
                if "error" not in extent:
                    layer_info["crs"] = extent.get("crs", "-")
                    if extent.get("extent"):
                        layer_info["extent"] = extent["extent"]
                # Merge: layer-specific info overrides top-level
                info = {**info, **layer_info}
            except Exception:
                pass

        self.app.call_from_thread(self._populate, info, layers, path)

    def _populate(self, info: dict, layers: list[str], path: str) -> None:
        """Populate metadata and data grid."""
        self.query_one(MetadataPanel).set_metadata(info)

        if layers and not self._is_raster:
            # Use requested layer if specified and valid, otherwise first layer
            target = self._requested_layer
            if target and target in layers:
                self._current_layer = target
            else:
                self._current_layer = layers[0]
            self._load_peek_data(self._current_layer)
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
        """Load dataset rows progressively in a background thread.

        Phase 1 — fast first paint:
            Fetch the first ``_INITIAL_ROWS`` rows with the existing ``peek()``
            call and render them immediately.

        Phase 2 — background streaming:
            If the handler exposes ``iter_rows()``, stream the remaining rows
            in ``_CHUNK_SIZE`` chunks, appending each chunk to the live table
            and updating the subtitle with load progress.
        """
        if self._handler is None:
            return

        # --- Phase 1: immediate render of first batch ---
        peek_data = self._handler.peek(limit=_INITIAL_ROWS, layer_name=layer_name)
        self.app.call_from_thread(self._show_peek_data, peek_data)

        total: int = peek_data.get("total_features", 0)
        loaded: int = peek_data.get("showing", 0)

        # Nothing more to stream (all rows already loaded, or no iter_rows)
        if loaded >= total or not hasattr(self._handler, "iter_rows"):
            return

        columns: list[str] = peek_data.get("columns", [])

        # --- Phase 2: stream remaining rows in chunks ---
        chunk: list[dict] = []
        for row in self._handler.iter_rows(layer_name=layer_name, skip=loaded):
            chunk.append(row)
            if len(chunk) >= _CHUNK_SIZE:
                loaded += len(chunk)
                self.app.call_from_thread(
                    self._append_rows, columns, list(chunk), loaded, total
                )
                chunk = []

        if chunk:
            loaded += len(chunk)
            self.app.call_from_thread(self._append_rows, columns, chunk, loaded, total)

        # Final subtitle once streaming is complete
        self.app.call_from_thread(self._finish_loading, loaded, total)

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
            if showing < total and hasattr(self._handler, "iter_rows"):
                grid_panel.border_subtitle = f"{showing:,} / {total:,} — loading..."
            else:
                grid_panel.border_subtitle = f"{showing:,} of {total:,} features"

            if not columns or not rows:
                return

            for col in columns:
                grid.add_column(col, key=col)

            for row in rows:
                grid.add_row(*[str(row.get(col, "")) for col in columns])

        except Exception:
            pass

    def _append_rows(
        self,
        columns: list[str],
        rows: list[dict],
        loaded: int,
        total: int,
    ) -> None:
        """Append a streaming chunk of rows to the live data grid."""
        try:
            grid = self.query_one("#data-grid", DataTable)
            grid_panel = self.query_one(GridPanel)
            for row in rows:
                grid.add_row(*[str(row.get(col, "")) for col in columns])
            grid_panel.border_subtitle = f"{loaded:,} / {total:,} — loading..."
        except Exception:
            pass

    def _finish_loading(self, loaded: int, total: int) -> None:
        """Update the subtitle once all rows have been streamed."""
        try:
            grid_panel = self.query_one(GridPanel)
            grid_panel.border_subtitle = f"{loaded:,} of {total:,} features"
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
