"""Geopeek TUI — interactive geospatial data explorer."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static, TabbedContent, TabPane

from geopeek.tui.theme import GEOPEEK_THEME
from geopeek.tui.widgets.explorer import ExplorerPanel
from geopeek.tui.widgets.data_panel import DataPanel


class GeopeekApp(App):
    """The main Geopeek TUI application."""

    TITLE = "geopeek"

    CSS_PATH = [
        "styles/index.tcss",
        "styles/app.tcss",
    ]

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("tab", "focus_next", "Next Panel", show=False),
        Binding("shift+tab", "focus_previous", "Prev Panel", show=False),
    ]

    def __init__(self, dataset_path: Optional[str] = None) -> None:
        super().__init__()
        self._initial_dataset = dataset_path

    def get_css_variables(self) -> dict[str, str]:
        """Inject our Catppuccin Mocha theme."""
        theme_vars = GEOPEEK_THEME.generate()
        return {**super().get_css_variables(), **theme_vars}

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="app-layout"):
            yield ExplorerPanel()
            with Vertical(id="content-area"):
                # Welcome panel — visible when no dataset is loaded
                yield Static(
                    "[bold]geopeek[/bold]\n\n"
                    "Select a geospatial dataset from\n"
                    "the explorer to get started.\n\n"
                    "[dim]Supported: .shp  .gdb  .tif  .tiff\n"
                    ".jp2  .png  .jpg  .img  .vrt  .dem[/dim]",
                    id="welcome-panel",
                    classes="module-container",
                )
                # Tabbed content — always composed, hidden until needed
                with TabbedContent(id="content-tabs"):
                    with TabPane("Attributes", id="tab-attributes"):
                        yield DataPanel()
        yield Footer()

    def on_mount(self) -> None:
        # Set welcome panel border title
        try:
            welcome = self.query_one("#welcome-panel", Static)
            welcome.border_title = "Welcome"
        except Exception:
            pass

        if self._initial_dataset:
            self._activate_dataset(self._initial_dataset)

    def _activate_dataset(self, path: str, layer_name: str | None = None) -> None:
        """Show tabs, hide welcome, and load the dataset."""
        if layer_name:
            self.sub_title = f"{Path(path).name} / {layer_name}"
        else:
            self.sub_title = Path(path).name

        # Hide welcome, show tabs
        try:
            welcome = self.query_one("#welcome-panel")
            welcome.display = False
        except Exception:
            pass
        try:
            tabs = self.query_one("#content-tabs")
            tabs.display = True
        except Exception:
            pass

        # Load data
        data_panel = self.query_one(DataPanel)
        data_panel.load_dataset(path, layer_name=layer_name)

    def on_explorer_panel_dataset_selected(
        self, event: ExplorerPanel.DatasetSelected
    ) -> None:
        """Handle dataset selection from the explorer."""
        self._activate_dataset(event.path, layer_name=event.layer_name)

    def action_refresh(self) -> None:
        """Reload the current dataset."""
        try:
            data_panel = self.query_one(DataPanel)
            data_panel.rebuild()
        except Exception:
            pass


def run_tui(dataset_path: Optional[str] = None) -> None:
    """Entry point to launch the TUI."""
    app = GeopeekApp(dataset_path=dataset_path)
    app.run()
