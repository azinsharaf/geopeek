"""Vim-enhanced DataTable and shared SearchInput widget."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual import events
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual.message import Message
from textual.widgets import DataTable, Input

from geopeek.tui.theme import CATPPUCCIN_MOCHA

if TYPE_CHECKING:
    from typing import Self


# Derive highlight colours directly from the theme palette so they stay in
# sync if the palette is ever updated.
_ROW_BG = CATPPUCCIN_MOCHA["surface1"]  # subtle tint on every cell in a matched row
_HIT_BG = CATPPUCCIN_MOCHA["yellow"]  # background on the matched substring itself


class SearchInput(Input):
    """A search Input that posts Dismissed when Escape is pressed."""

    class Dismissed(Message):
        """Posted when the user presses Escape to cancel the search."""

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            event.stop()
            self.post_message(self.Dismissed())


class VimDataTable(DataTable):
    """DataTable with vim-style navigation, inline search, and match highlighting.

    Key bindings added on top of the standard DataTable:
      j / k          — cursor down / up
      h / l          — scroll left / right
      g,g            — jump to first row
      G              — jump to last row
      ctrl+d         — half-page down
      ctrl+u         — half-page up
      z,z            — center cursor row in viewport
      /              — open inline search bar (handled by parent GridPanel)
      n / N          — next / previous search match

    Matching rows are highlighted: the whole row gets a subtle background and
    the matched substring is bolded with a yellow background.  All highlights
    are cleared when the query changes or the table is repopulated.
    """

    class SearchRequested(Message):
        """Posted when / is pressed; parent should show the search input."""

    BINDINGS = [
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
        Binding("h", "vim_scroll_left", show=False),
        Binding("l", "vim_scroll_right", show=False),
        Binding("g,g", "vim_top", show=False),
        Binding("G", "vim_bottom", show=False),
        Binding("ctrl+d", "vim_half_down", show=False),
        Binding("ctrl+u", "vim_half_up", show=False),
        Binding("z,z", "vim_center", show=False),
        Binding("/", "vim_search", show=False),
        Binding("n", "vim_search_next", show=False),
        Binding("N", "vim_search_prev", show=False),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._search_matches: list[int] = []
        self._search_idx: int = -1
        # row_idx → list of original plain-string cell values (saved before
        # we overwrite cells with Rich Text for highlighting)
        self._original_cells: dict[int, list[str]] = {}
        self._highlighted_rows: set[int] = set()

    # ------------------------------------------------------------------
    # Vim actions
    # ------------------------------------------------------------------

    def action_vim_scroll_left(self) -> None:
        """h — scroll the table view left by one column width."""
        self.scroll_left(animate=False)

    def action_vim_scroll_right(self) -> None:
        """l — scroll the table view right by one column width."""
        self.scroll_right(animate=False)

    def action_vim_top(self) -> None:
        """g,g — jump to the first row."""
        if self.row_count > 0:
            self.move_cursor(row=0)

    def action_vim_bottom(self) -> None:
        """G — jump to the last row."""
        if self.row_count > 0:
            self.move_cursor(row=self.row_count - 1)

    def action_vim_half_down(self) -> None:
        """ctrl+d — move cursor down by half the visible height."""
        half = max(1, self.size.height // 2)
        new_row = min(self.row_count - 1, self.cursor_row + half)
        self.move_cursor(row=new_row)

    def action_vim_half_up(self) -> None:
        """ctrl+u — move cursor up by half the visible height."""
        half = max(1, self.size.height // 2)
        new_row = max(0, self.cursor_row - half)
        self.move_cursor(row=new_row)

    def action_vim_center(self) -> None:
        """z,z — scroll so the cursor row is centred in the viewport."""
        center_y = max(0, self.cursor_row - self.size.height // 2)
        self.scroll_to(y=center_y, animate=False)

    def action_vim_search(self) -> None:
        """/ — ask the parent panel to show the search bar."""
        self.post_message(self.SearchRequested())

    def action_vim_search_next(self) -> None:
        """n — jump to the next search match."""
        if not self._search_matches:
            return
        self._search_idx = (self._search_idx + 1) % len(self._search_matches)
        self.move_cursor(row=self._search_matches[self._search_idx])

    def action_vim_search_prev(self) -> None:
        """N — jump to the previous search match."""
        if not self._search_matches:
            return
        self._search_idx = (self._search_idx - 1) % len(self._search_matches)
        self.move_cursor(row=self._search_matches[self._search_idx])

    # ------------------------------------------------------------------
    # Search + highlight logic
    # ------------------------------------------------------------------

    def jump_to_search(self, query: str) -> None:
        """Collect rows containing *query*, highlight them, jump to the first."""
        self._clear_highlights()
        self._search_matches = []
        self._search_idx = -1

        if not query:
            return

        q = query.lower()
        for idx in range(self.row_count):
            try:
                row_data = self.get_row_at(idx)
                if any(q in str(cell).lower() for cell in row_data):
                    self._search_matches.append(idx)
            except Exception:
                continue

        self._apply_highlights(query)

        if self._search_matches:
            self._search_idx = 0
            self.move_cursor(row=self._search_matches[0])

    def clear(self, columns: bool = False) -> Self:
        """Override to reset highlight state when the table is repopulated."""
        self._original_cells.clear()
        self._highlighted_rows.clear()
        self._search_matches = []
        self._search_idx = -1
        return super().clear(columns=columns)

    # ------------------------------------------------------------------
    # Internal highlight helpers
    # ------------------------------------------------------------------

    def _apply_highlights(self, query: str) -> None:
        """Write highlighted Rich Text into every cell of every matched row."""
        for row_idx in self._search_matches:
            self._save_original_row(row_idx)
            originals = self._original_cells.get(row_idx, [])
            for col_idx, raw in enumerate(originals):
                cell = self._make_highlighted_cell(raw, query)
                try:
                    self.update_cell_at(
                        Coordinate(row_idx, col_idx),
                        cell,
                        update_width=False,
                    )
                except Exception:
                    pass
            self._highlighted_rows.add(row_idx)

    def _clear_highlights(self) -> None:
        """Restore all previously highlighted cells to plain strings."""
        for row_idx in list(self._highlighted_rows):
            originals = self._original_cells.get(row_idx, [])
            for col_idx, raw in enumerate(originals):
                try:
                    self.update_cell_at(
                        Coordinate(row_idx, col_idx),
                        raw,
                        update_width=False,
                    )
                except Exception:
                    pass
        self._highlighted_rows.clear()

    def _save_original_row(self, row_idx: int) -> None:
        """Snapshot a row's plain-string values before highlighting overwrites them."""
        if row_idx in self._original_cells:
            return  # already saved
        try:
            self._original_cells[row_idx] = [
                str(cell) for cell in self.get_row_at(row_idx)
            ]
        except Exception:
            pass

    @staticmethod
    def _make_highlighted_cell(value: str, query: str) -> Text:
        """Build a Rich Text for one cell.

        Every character gets the subtle row-background tint (_ROW_BG).
        Characters that form part of the matched substring additionally get
        the yellow hit-background (_HIT_BG) and bold weight.
        """
        text = Text()
        lower_val = value.lower()
        lower_q = query.lower()
        start = 0
        while (idx := lower_val.find(lower_q, start)) != -1:
            if idx > start:
                text.append(value[start:idx], style=f"on {_ROW_BG}")
            text.append(
                value[idx : idx + len(query)],
                style=f"bold on {_HIT_BG}",
            )
            start = idx + len(query)
        text.append(value[start:], style=f"on {_ROW_BG}")
        return text
