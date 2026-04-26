"""Fields panel — displays the field/band schema for a loaded dataset."""

from __future__ import annotations

from typing import Optional

from textual import work
from textual.app import ComposeResult
from textual.widgets import DataTable, Static

from geopeek.tui.widgets.vim_table import SearchInput, VimDataTable


# Column definitions: (key, header label, width hint)
_VECTOR_COLUMNS = [
    ("name", "Name", 20),
    ("alias", "Alias", 20),
    ("type", "Type", 12),
    ("width", "Width", 7),
    ("precision", "Precision", 9),
    ("nullable", "Nullable", 8),
]

_RASTER_COLUMNS = [
    ("band", "Band", 6),
    ("type", "Type", 12),
    ("nodata", "NoData", 10),
    ("min", "Min", 10),
    ("max", "Max", 10),
]


class FieldsPanel(Static):
    """Bordered card showing field schema (vector) or band schema (raster).

    Call ``load_dataset(path, layer_name)`` to populate.
    """

    can_focus = False  # Focus goes to the VimDataTable inside

    def __init__(self) -> None:
        super().__init__(id="fields-panel", classes="module-container")
        self.border_title = "Fields"
        self.border_subtitle = ""
        self._handler = None

    def compose(self) -> ComposeResult:
        yield VimDataTable(id="fields-grid")
        search = SearchInput(placeholder="/  search fields...", id="fields-search")
        search.display = False
        yield search

    def on_mount(self) -> None:
        grid = self.query_one("#fields-grid", VimDataTable)
        grid.cursor_type = "row"
        grid.show_cursor = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_dataset(self, path: str, layer_name: Optional[str] = None) -> None:
        """Start loading schema for *path* / *layer_name* in a background thread."""
        self._load_schema(path, layer_name)

    def clear(self) -> None:
        """Reset to empty state."""
        try:
            grid = self.query_one("#fields-grid", VimDataTable)
            grid.clear(columns=True)
            self.border_subtitle = ""
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Background loading
    # ------------------------------------------------------------------

    @work(thread=True)
    def _load_schema(self, path: str, layer_name: Optional[str] = None) -> None:
        """Fetch schema in a background thread and populate the grid."""
        from geopeek.tui.widgets.data_panel import DataPanel

        handler = DataPanel._select_handler(path)
        if handler is None:
            return
        self._handler = handler

        # Detect raster
        is_raster = path.lower().endswith(
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

        if is_raster:
            info = handler.get_info()
            bands = info.get("bands", [])
            self.app.call_from_thread(self._show_raster_bands, bands)
        else:
            schema = handler.get_schema(layer_name=layer_name)
            self.app.call_from_thread(self._show_fields, schema, layer_name)

    # ------------------------------------------------------------------
    # Grid population (main thread)
    # ------------------------------------------------------------------

    def _show_fields(self, schema: dict, layer_name: Optional[str]) -> None:
        """Populate the grid with vector field definitions."""
        try:
            grid = self.query_one("#fields-grid", VimDataTable)
            grid.clear(columns=True)

            if "error" in schema:
                self.border_subtitle = f"error: {schema['error']}"
                return

            fields = schema.get("fields", [])
            if not fields:
                self.border_subtitle = "no fields"
                return

            for key, label, width in _VECTOR_COLUMNS:
                grid.add_column(label, key=key, width=width)

            for field in fields:
                grid.add_row(
                    field.get("name", ""),
                    field.get("alias", ""),
                    field.get("type", ""),
                    str(field.get("width", "")),
                    str(field.get("precision", "")),
                    "yes" if field.get("nullable", True) else "no",
                )

            n = len(fields)
            layer = schema.get("layer") or layer_name or ""
            self.border_subtitle = f"{n} field{'s' if n != 1 else ''}" + (
                f"  ·  {layer}" if layer else ""
            )
        except Exception:
            pass

    def _show_raster_bands(self, bands: list) -> None:
        """Populate the grid with raster band info."""
        try:
            grid = self.query_one("#fields-grid", VimDataTable)
            grid.clear(columns=True)

            if not bands:
                self.border_subtitle = "no band info"
                return

            for key, label, width in _RASTER_COLUMNS:
                grid.add_column(label, key=key, width=width)

            for band in bands:
                grid.add_row(
                    str(band.get("band", "")),
                    str(band.get("type", "")),
                    str(band.get("nodata", "")),
                    str(band.get("min", "")),
                    str(band.get("max", "")),
                )

            n = len(bands)
            self.border_subtitle = f"{n} band{'s' if n != 1 else ''}"
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Search bar — mirrors GridPanel pattern
    # ------------------------------------------------------------------

    def on_vim_data_table_search_requested(
        self, event: VimDataTable.SearchRequested
    ) -> None:
        event.stop()
        search = self.query_one("#fields-search", SearchInput)
        search.display = True
        search.value = ""
        search.focus()

    def on_input_changed(self, event: SearchInput.Changed) -> None:
        if event.input.id == "fields-search":
            self.query_one("#fields-grid", VimDataTable).jump_to_search(event.value)

    def on_input_submitted(self, event: SearchInput.Submitted) -> None:
        if event.input.id == "fields-search":
            self._hide_search()

    def on_search_input_dismissed(self, event: SearchInput.Dismissed) -> None:
        self._hide_search()

    def _hide_search(self) -> None:
        search = self.query_one("#fields-search", SearchInput)
        search.display = False
        self.query_one("#fields-grid", VimDataTable).focus()
