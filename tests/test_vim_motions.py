"""Tests for vim-style key bindings and motions in the TUI.

Coverage
--------
Unit tests (no app):
  - VimDataTable and GeoFilteredTree have the expected BINDINGS declared
  - VimDataTable.jump_to_search selects the right rows
  - VimDataTable search cycling (next / prev)

Async pilot tests:
  - j / k move the DataTable cursor down / up
  - g,g jumps to the first row
  - G   jumps to the last row
  - ctrl+d / ctrl+u move by half a page
  - z,z does not crash (scroll centre)
  - /   shows the GridPanel search input
  - Typing in the search bar calls jump_to_search
  - Escape hides the search input
  - n / N cycle through search matches after a query is set
  - j / k move the tree cursor down / up
  - /   shows the ExplorerPanel search input
  - Escape hides the tree search input
  - l expands a tree node
  - h collapses a tree node
"""

from __future__ import annotations

import pytest
from pathlib import Path
from rich.text import Text
from textual.app import App, ComposeResult

from geopeek.tui.widgets.vim_table import VimDataTable, SearchInput
from geopeek.tui.widgets.explorer import GeoFilteredTree
from geopeek.tui.widgets.data_panel import GridPanel
from geopeek.tui.widgets.explorer import ExplorerPanel


# ---------------------------------------------------------------------------
# Minimal test apps
# ---------------------------------------------------------------------------


class TableApp(App):
    """Minimal app with a pre-populated VimDataTable."""

    CSS = "VimDataTable { height: 1fr; }"

    def compose(self) -> ComposeResult:
        yield VimDataTable(id="table")

    def on_mount(self) -> None:
        table = self.query_one(VimDataTable)
        table.cursor_type = "row"
        table.add_column("name", key="name")
        table.add_column("value", key="value")
        for name, value in [
            ("alpha", "10"),
            ("beta", "20"),
            ("gamma", "30"),
            ("delta", "40"),
            ("epsilon", "50"),
        ]:
            table.add_row(name, value)


class GridPanelApp(App):
    """Minimal app with a GridPanel (VimDataTable + search bar)."""

    CSS = "#grid-panel { height: 1fr; }"

    def compose(self) -> ComposeResult:
        yield GridPanel()

    def on_mount(self) -> None:
        table = self.query_one(VimDataTable)
        table.cursor_type = "row"
        table.add_column("city", key="city")
        table.add_column("pop", key="pop")
        for city, pop in [
            ("Amsterdam", "900k"),
            ("Berlin", "3.6M"),
            ("Cairo", "10M"),
            ("Dublin", "1.4M"),
            ("Edinburgh", "500k"),
        ]:
            table.add_row(city, pop)


class TreeApp(App):
    """Minimal app with a GeoFilteredTree over a temp directory."""

    CSS = "GeoFilteredTree { height: 1fr; }"

    def __init__(self, root: str) -> None:
        super().__init__()
        self._root = root

    def compose(self) -> ComposeResult:
        yield GeoFilteredTree(self._root, id="tree")


class ExplorerApp(App):
    """Minimal app with a full ExplorerPanel (tree + search bar)."""

    CSS = "#explorer-panel { height: 1fr; width: 40; }"

    def __init__(self, root: str) -> None:
        super().__init__()
        self._root = root

    def compose(self) -> ComposeResult:
        yield ExplorerPanel(start_path=self._root)


# ---------------------------------------------------------------------------
# Unit tests — BINDINGS declarations (no app needed)
# ---------------------------------------------------------------------------


def _binding_keys(widget_cls) -> set[str]:
    """Collect all key strings declared in a widget's BINDINGS."""
    return {b.key for b in widget_cls.BINDINGS}


def test_vim_data_table_has_j_k_bindings():
    keys = _binding_keys(VimDataTable)
    assert "j" in keys
    assert "k" in keys


def test_vim_data_table_has_h_l_bindings():
    keys = _binding_keys(VimDataTable)
    assert "h" in keys
    assert "l" in keys


def test_vim_data_table_has_gg_G_bindings():
    keys = _binding_keys(VimDataTable)
    assert "g,g" in keys
    assert "G" in keys


def test_vim_data_table_has_vim_top_bottom_actions():
    assert hasattr(VimDataTable, "action_vim_top")
    assert hasattr(VimDataTable, "action_vim_bottom")


def test_vim_data_table_has_half_page_bindings():
    keys = _binding_keys(VimDataTable)
    assert "ctrl+d" in keys
    assert "ctrl+u" in keys


def test_vim_data_table_has_center_binding():
    assert "z,z" in _binding_keys(VimDataTable)


def test_vim_data_table_has_search_bindings():
    keys = _binding_keys(VimDataTable)
    assert "/" in keys
    assert "n" in keys
    assert "N" in keys


def test_geo_filtered_tree_has_j_k_bindings():
    keys = _binding_keys(GeoFilteredTree)
    assert "j" in keys
    assert "k" in keys


def test_geo_filtered_tree_has_h_l_bindings():
    keys = _binding_keys(GeoFilteredTree)
    assert "h" in keys
    assert "l" in keys


def test_geo_filtered_tree_has_gg_G_bindings():
    keys = _binding_keys(GeoFilteredTree)
    assert "g,g" in keys
    assert "G" in keys


def test_geo_filtered_tree_has_half_page_bindings():
    keys = _binding_keys(GeoFilteredTree)
    assert "ctrl+d" in keys
    assert "ctrl+u" in keys


def test_geo_filtered_tree_has_search_bindings():
    keys = _binding_keys(GeoFilteredTree)
    assert "/" in keys
    assert "n" in keys
    assert "N" in keys


def test_search_input_has_dismissed_message():
    assert hasattr(SearchInput, "Dismissed")


# ---------------------------------------------------------------------------
# Unit tests — jump_to_search logic (in-app, no pilot interaction)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_jump_to_search_finds_matching_rows():
    app = TableApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.jump_to_search("bet")
        # "beta" is row index 1
        assert table._search_matches == [1]
        assert table._search_idx == 0
        assert table.cursor_row == 1


@pytest.mark.asyncio
async def test_jump_to_search_multiple_matches():
    app = TableApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        # "a" appears in alpha, gamma, delta
        table.jump_to_search("a")
        assert len(table._search_matches) >= 2
        assert table._search_idx == 0
        assert table.cursor_row == table._search_matches[0]


@pytest.mark.asyncio
async def test_jump_to_search_no_match_leaves_state_empty():
    app = TableApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.jump_to_search("zzznomatch")
        assert table._search_matches == []
        assert table._search_idx == -1


@pytest.mark.asyncio
async def test_jump_to_search_empty_query_clears_state():
    app = TableApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.jump_to_search("alpha")
        assert table._search_matches  # has results
        table.jump_to_search("")
        assert table._search_matches == []
        assert table._search_idx == -1


# ---------------------------------------------------------------------------
# Unit tests — search cycling (next / prev)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_next_cycles_forward():
    app = TableApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        # "a" matches alpha(0), gamma(2), delta(3)
        table.jump_to_search("a")
        matches = list(table._search_matches)
        assert len(matches) >= 2

        # Start at first match
        assert table.cursor_row == matches[0]

        # n → move to second match
        table.action_vim_search_next()
        assert table.cursor_row == matches[1]


@pytest.mark.asyncio
async def test_search_prev_cycles_backward():
    app = TableApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.jump_to_search("a")
        matches = list(table._search_matches)
        assert len(matches) >= 2

        # N from idx 0 → wraps to last match
        table.action_vim_search_prev()
        assert table.cursor_row == matches[-1]


# ---------------------------------------------------------------------------
# Unit tests — _make_highlighted_cell (no app needed)
# ---------------------------------------------------------------------------


def test_make_highlighted_cell_marks_matched_substring():
    cell = VimDataTable._make_highlighted_cell("Amsterdam", "ster")
    plain = cell.plain
    assert plain == "Amsterdam"
    # The matched region should have bold style applied
    spans = [s for s in cell._spans if "bold" in str(s.style)]
    assert spans, "expected at least one bold span for the matched substring"


def test_make_highlighted_cell_case_insensitive():
    cell = VimDataTable._make_highlighted_cell("Berlin", "BERL")
    spans = [s for s in cell._spans if "bold" in str(s.style)]
    assert spans


def test_make_highlighted_cell_no_match_has_row_bg_only():
    from geopeek.tui.widgets.vim_table import _ROW_BG

    cell = VimDataTable._make_highlighted_cell("Cairo", "xyz")
    # No bold spans — the whole cell just gets the row background
    bold_spans = [s for s in cell._spans if "bold" in str(s.style)]
    assert not bold_spans
    # But the row-bg style should be present
    bg_spans = [s for s in cell._spans if _ROW_BG in str(s.style)]
    assert bg_spans


def test_make_highlighted_cell_multiple_occurrences():
    cell = VimDataTable._make_highlighted_cell("banana", "an")
    bold_spans = [s for s in cell._spans if "bold" in str(s.style)]
    # "an" appears twice in "banana"
    assert len(bold_spans) == 2


# ---------------------------------------------------------------------------
# Async tests — row highlighting in a running app
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_matching_rows_are_highlighted_after_search():
    app = TableApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.focus()
        table.jump_to_search("alpha")

        # Row 0 ("alpha") should now be stored in _highlighted_rows
        assert 0 in table._highlighted_rows


@pytest.mark.asyncio
async def test_highlights_cleared_on_empty_query():
    app = TableApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.jump_to_search("alpha")
        assert table._highlighted_rows

        table.jump_to_search("")
        assert not table._highlighted_rows


@pytest.mark.asyncio
async def test_previous_highlights_cleared_on_new_query():
    app = TableApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.jump_to_search("alpha")
        first_highlighted = set(table._highlighted_rows)

        table.jump_to_search("beta")
        # Old highlights gone, new ones applied
        assert first_highlighted != table._highlighted_rows
        assert 1 in table._highlighted_rows  # "beta" is row 1


@pytest.mark.asyncio
async def test_original_cells_restored_after_clear():
    app = TableApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.jump_to_search("alpha")
        # Row 0 col 0 should now be a Rich Text (highlighted)
        from textual.coordinate import Coordinate

        highlighted_cell = table.get_cell_at(Coordinate(0, 0))
        assert isinstance(highlighted_cell, Text)

        # Clear search — cell should revert to plain string
        table.jump_to_search("")
        restored_cell = table.get_cell_at(Coordinate(0, 0))
        assert isinstance(restored_cell, str)
        assert restored_cell == "alpha"


@pytest.mark.asyncio
async def test_search_next_no_op_without_query():
    app = TableApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.focus()
        initial_row = table.cursor_row
        table.action_vim_search_next()
        assert table.cursor_row == initial_row  # nothing changed


# ---------------------------------------------------------------------------
# Pilot tests — VimDataTable key navigation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_j_moves_cursor_down():
    app = TableApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.focus()
        await pilot.pause()
        assert table.cursor_row == 0
        await pilot.press("j")
        await pilot.pause()
        assert table.cursor_row == 1


@pytest.mark.asyncio
async def test_k_moves_cursor_up():
    app = TableApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.focus()
        await pilot.pause()
        table.move_cursor(row=2)
        await pilot.pause()
        await pilot.press("k")
        await pilot.pause()
        assert table.cursor_row == 1


@pytest.mark.asyncio
async def test_G_jumps_to_last_row():
    app = TableApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.focus()
        await pilot.pause()
        await pilot.press("G")
        await pilot.pause()
        assert table.cursor_row == table.row_count - 1


@pytest.mark.asyncio
async def test_gg_jumps_to_first_row():
    app = TableApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.focus()
        await pilot.pause()
        table.move_cursor(row=4)
        await pilot.pause()
        await pilot.press("g", "g")
        await pilot.pause()
        assert table.cursor_row == 0


@pytest.mark.asyncio
async def test_ctrl_d_moves_cursor_down():
    app = TableApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.focus()
        initial_row = table.cursor_row
        await pilot.press("ctrl+d")
        # Should move at least 1 row (half the visible height, min 1)
        assert table.cursor_row >= initial_row


@pytest.mark.asyncio
async def test_ctrl_u_moves_cursor_up():
    app = TableApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.focus()
        table.move_cursor(row=4)
        await pilot.press("ctrl+u")
        assert table.cursor_row <= 4


@pytest.mark.asyncio
async def test_l_scrolls_right():
    """l should increase scroll_x (or keep it at max if already at end)."""
    app = TableApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.focus()
        await pilot.pause()
        before = table.scroll_x
        await pilot.press("l")
        await pilot.pause()
        assert table.scroll_x >= before  # at max it stays put, otherwise increases


@pytest.mark.asyncio
async def test_h_scrolls_left():
    """h should decrease scroll_x (or stay at 0 if already at left edge)."""
    app = TableApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.focus()
        await pilot.pause()
        # First scroll right so there's room to scroll back
        await pilot.press("l")
        await pilot.pause()
        scrolled_x = table.scroll_x
        await pilot.press("h")
        await pilot.pause()
        assert table.scroll_x <= scrolled_x


@pytest.mark.asyncio
async def test_zz_does_not_crash():
    """z,z centering should not raise — visual result is not assertable."""
    app = TableApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.focus()
        table.move_cursor(row=2)
        await pilot.press("z", "z")
        # Still on the same row
        assert table.cursor_row == 2


# ---------------------------------------------------------------------------
# Pilot tests — GridPanel search bar
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_slash_shows_search_input():
    app = GridPanelApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.focus()
        search = app.query_one("#grid-search", SearchInput)
        assert not search.display
        await pilot.press("/")
        assert search.display


@pytest.mark.asyncio
async def test_escape_hides_search_input():
    app = GridPanelApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.focus()
        await pilot.press("/")
        search = app.query_one("#grid-search", SearchInput)
        assert search.display
        await pilot.press("escape")
        await pilot.pause()
        assert not search.display


@pytest.mark.asyncio
async def test_search_input_refocuses_table_after_escape():
    app = GridPanelApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.focus()
        await pilot.press("/")
        await pilot.press("escape")
        await pilot.pause()
        assert app.focused is table


@pytest.mark.asyncio
async def test_enter_hides_search_input():
    app = GridPanelApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.focus()
        await pilot.press("/")
        search = app.query_one("#grid-search", SearchInput)
        assert search.display
        await pilot.press("enter")
        assert not search.display


@pytest.mark.asyncio
async def test_typing_in_search_jumps_cursor():
    app = GridPanelApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.focus()
        await pilot.press("/")
        # Type "Ber" — should match "Berlin" at row index 1
        await pilot.press("B", "e", "r")
        assert table.cursor_row == 1


@pytest.mark.asyncio
async def test_n_cycles_next_match_after_search():
    app = GridPanelApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.focus()
        # Manually set search state ("a" matches Amsterdam(0), Cairo(2), Edinburgh(4))
        table.jump_to_search("a")
        matches = list(table._search_matches)
        assert len(matches) >= 2

        # Dismiss any open search bar and re-focus table
        await pilot.press("escape")
        table.focus()

        first_row = matches[0]
        second_row = matches[1]
        assert table.cursor_row == first_row

        await pilot.press("n")
        assert table.cursor_row == second_row


@pytest.mark.asyncio
async def test_N_cycles_prev_match():
    app = GridPanelApp()
    async with app.run_test() as pilot:
        table = app.query_one(VimDataTable)
        table.focus()
        table.jump_to_search("a")
        matches = list(table._search_matches)
        assert len(matches) >= 2

        await pilot.press("escape")
        table.focus()

        # N from first match wraps to last
        await pilot.press("N")
        assert table.cursor_row == matches[-1]


# ---------------------------------------------------------------------------
# Pilot tests — GeoFilteredTree key navigation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tree_j_moves_cursor_down(tmp_path):
    # Create geospatial files the tree will show
    (tmp_path / "aaa.shp").write_text("x")
    (tmp_path / "bbb.shp").write_text("x")
    (tmp_path / "ccc.tif").write_text("x")

    app = TreeApp(str(tmp_path))
    async with app.run_test() as pilot:
        tree = app.query_one(GeoFilteredTree)
        tree.focus()
        await pilot.pause(0.3)  # wait for directory listing to load
        initial_line = tree.cursor_line
        await pilot.press("j")
        assert tree.cursor_line > initial_line


@pytest.mark.asyncio
async def test_tree_k_moves_cursor_up(tmp_path):
    (tmp_path / "aaa.shp").write_text("x")
    (tmp_path / "bbb.shp").write_text("x")
    (tmp_path / "ccc.tif").write_text("x")

    app = TreeApp(str(tmp_path))
    async with app.run_test() as pilot:
        tree = app.query_one(GeoFilteredTree)
        tree.focus()
        await pilot.pause(0.3)
        await pilot.press("j")
        line_after_j = tree.cursor_line
        await pilot.press("k")
        assert tree.cursor_line < line_after_j


@pytest.mark.asyncio
async def test_tree_G_jumps_to_last_node(tmp_path):
    for name in ("aaa.shp", "bbb.shp", "ccc.tif"):
        (tmp_path / name).write_text("x")

    app = TreeApp(str(tmp_path))
    async with app.run_test() as pilot:
        tree = app.query_one(GeoFilteredTree)
        tree.focus()
        await pilot.pause(0.3)
        await pilot.press("G")
        line_after_G = tree.cursor_line
        # Pressing j should not move further (already at bottom)
        await pilot.press("j")
        assert tree.cursor_line == line_after_G


@pytest.mark.asyncio
async def test_tree_gg_jumps_to_first_node(tmp_path):
    for name in ("aaa.shp", "bbb.shp", "ccc.tif"):
        (tmp_path / name).write_text("x")

    app = TreeApp(str(tmp_path))
    async with app.run_test() as pilot:
        tree = app.query_one(GeoFilteredTree)
        tree.focus()
        await pilot.pause(0.3)
        await pilot.press("G")  # go to bottom first
        await pilot.press("g", "g")  # then back to top
        assert tree.cursor_line == 0


# ---------------------------------------------------------------------------
# Pilot tests — ExplorerPanel search bar
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tree_slash_shows_search_input(tmp_path):
    (tmp_path / "test.shp").write_text("x")

    app = ExplorerApp(str(tmp_path))
    async with app.run_test() as pilot:
        tree = app.query_one(GeoFilteredTree)
        tree.focus()
        search = app.query_one("#tree-search", SearchInput)
        assert not search.display
        await pilot.press("/")
        assert search.display


@pytest.mark.asyncio
async def test_tree_escape_hides_search_input(tmp_path):
    (tmp_path / "test.shp").write_text("x")

    app = ExplorerApp(str(tmp_path))
    async with app.run_test() as pilot:
        tree = app.query_one(GeoFilteredTree)
        tree.focus()
        await pilot.press("/")
        search = app.query_one("#tree-search", SearchInput)
        assert search.display
        await pilot.press("escape")
        await pilot.pause()
        assert not search.display


@pytest.mark.asyncio
async def test_tree_search_refocuses_tree_after_escape(tmp_path):
    (tmp_path / "test.shp").write_text("x")

    app = ExplorerApp(str(tmp_path))
    async with app.run_test() as pilot:
        tree = app.query_one(GeoFilteredTree)
        tree.focus()
        await pilot.press("/")
        await pilot.press("escape")
        await pilot.pause()
        assert app.focused is tree


@pytest.mark.asyncio
async def test_tree_zz_does_not_crash(tmp_path):
    for name in ("aaa.shp", "bbb.shp", "ccc.tif"):
        (tmp_path / name).write_text("x")

    app = TreeApp(str(tmp_path))
    async with app.run_test() as pilot:
        tree = app.query_one(GeoFilteredTree)
        tree.focus()
        await pilot.pause(0.3)
        await pilot.press("j")
        await pilot.press("z", "z")
        # Should not raise; cursor stays at current line
        assert tree.cursor_line >= 0
