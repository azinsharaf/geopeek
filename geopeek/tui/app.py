"""Geopeek TUI — interactive geospatial data explorer."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static, TabbedContent, TabPane, Tabs

from geopeek.tui.theme import GEOPEEK_THEME
from geopeek.tui.widgets.explorer import ExplorerPanel
from geopeek.tui.widgets.data_panel import DataPanel
from geopeek.tui.widgets.fields_panel import FieldsPanel


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
                    with TabPane("Fields", id="tab-fields"):
                        yield FieldsPanel()
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

        # Load data into both panels
        data_panel = self.query_one(DataPanel)
        data_panel.load_dataset(path, layer_name=layer_name)

        fields_panel = self.query_one(FieldsPanel)
        fields_panel.load_dataset(path, layer_name=layer_name)

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

    # ------------------------------------------------------------------
    # Custom Tab / Shift+Tab focus cycle
    #
    # Tab:       explorer → Attributes tab bar → Fields tab bar → explorer
    # Shift+Tab: reverse
    # ------------------------------------------------------------------

    def action_focus_next(self) -> None:
        """Tab: tree → Attributes tab → Fields tab → tree."""
        focused = self.focused
        try:
            tabs_widget = self.query_one(Tabs)
            tabbed = self.query_one("#content-tabs", TabbedContent)
        except Exception:
            super().action_focus_next()
            return

        if focused is not None and focused.id == "dir-tree":
            # tree → Attributes tab bar
            tabbed.active = "tab-attributes"
            tabs_widget.focus()
        elif isinstance(focused, Tabs):
            if tabbed.active == "tab-attributes":
                # Attributes → Fields tab bar (switch tab, keep focus on bar)
                tabbed.active = "tab-fields"
            else:
                # Fields → back to explorer
                try:
                    self.query_one("#dir-tree").focus()
                except Exception:
                    pass
        else:
            super().action_focus_next()

    def action_focus_previous(self) -> None:
        """Shift+Tab: tree → Fields tab → Attributes tab → tree (reverse)."""
        focused = self.focused
        try:
            tabs_widget = self.query_one(Tabs)
            tabbed = self.query_one("#content-tabs", TabbedContent)
        except Exception:
            super().action_focus_previous()
            return

        if focused is not None and focused.id == "dir-tree":
            # tree → Fields tab bar (end of cycle)
            tabbed.active = "tab-fields"
            tabs_widget.focus()
        elif isinstance(focused, Tabs):
            if tabbed.active == "tab-fields":
                # Fields → Attributes tab bar
                tabbed.active = "tab-attributes"
            else:
                # Attributes → back to explorer
                try:
                    self.query_one("#dir-tree").focus()
                except Exception:
                    pass
        else:
            super().action_focus_previous()

    # ------------------------------------------------------------------
    # h / l / Enter on the tab bar
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Focus hint — show a contextual tip in the header subtitle when
    # the tab bar is focused so users know how to navigate
    # ------------------------------------------------------------------

    def on_descendant_focus(self, event: events.DescendantFocus) -> None:
        if isinstance(event.widget, Tabs):
            self._pre_hint_subtitle = self.sub_title
            self.sub_title = "enter → grid  ·  h/l  ←/→  switch tab"

    def on_descendant_blur(self, event: events.DescendantBlur) -> None:
        if isinstance(event.widget, Tabs):
            self.sub_title = getattr(self, "_pre_hint_subtitle", "")

    # ------------------------------------------------------------------
    # h / l / Enter on the tab bar
    # ------------------------------------------------------------------

    def on_key(self, event: events.Key) -> None:
        """Handle h/l/Enter when the tab bar has focus.

        left/right arrow keys are already handled natively by Textual's
        Tabs widget; we only need to add the vim h/l aliases and Enter.
        """
        if not isinstance(self.focused, Tabs):
            return
        try:
            tabbed = self.query_one("#content-tabs", TabbedContent)
        except Exception:
            return

        if event.key == "h":
            tabbed.action_previous_tab()
            event.stop()
        elif event.key == "l":
            tabbed.action_next_tab()
            event.stop()
        elif event.key == "enter":
            # Dive into the active tab's grid
            target_id = (
                "data-grid" if tabbed.active == "tab-attributes" else "fields-grid"
            )
            try:
                self.query_one(f"#{target_id}").focus()
            except Exception:
                pass
            event.stop()


def run_tui(dataset_path: Optional[str] = None) -> None:
    """Entry point to launch the TUI."""
    app = GeopeekApp(dataset_path=dataset_path)
    app.run()
