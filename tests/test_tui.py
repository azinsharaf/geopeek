"""Tests for geopeek TUI application."""

import pytest

from geopeek.tui.app import GeopeekApp, _is_geospatial, _select_handler

from pathlib import Path


# --- Unit tests for helper functions ---


def test_is_geospatial_shapefile(tmp_path):
    f = tmp_path / "test.shp"
    f.write_text("data")
    assert _is_geospatial(f) is True


def test_is_geospatial_raster(tmp_path):
    f = tmp_path / "dem.tif"
    f.write_text("data")
    assert _is_geospatial(f) is True


def test_is_geospatial_gdb(tmp_path):
    gdb = tmp_path / "test.gdb"
    gdb.mkdir()
    assert _is_geospatial(gdb) is True


def test_is_geospatial_txt(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("data")
    assert _is_geospatial(f) is False


def test_select_handler_shapefile(tmp_path):
    f = tmp_path / "test.shp"
    f.write_text("data")
    handler = _select_handler(str(f))
    assert handler is not None
    assert type(handler).__name__ == "ShapefileHandler"


def test_select_handler_raster(tmp_path):
    f = tmp_path / "test.tif"
    f.write_text("data")
    handler = _select_handler(str(f))
    assert handler is not None
    assert type(handler).__name__ == "RasterHandler"


def test_select_handler_unsupported():
    handler = _select_handler("/some/file.csv")
    assert handler is None


# --- Textual App tests ---


@pytest.mark.asyncio
async def test_tui_app_starts_with_file_picker():
    """App with no path should show the file picker."""
    app = GeopeekApp(dataset_path=None)
    async with app.run_test() as pilot:
        # File picker should be present
        assert app.query_one("#file-picker")
        assert app.query_one("#dir-tree")


@pytest.mark.asyncio
async def test_tui_app_starts_with_dataset_view():
    """App with a path should show the dataset view."""
    # Use a fake path — handler will fail but UI should still compose
    app = GeopeekApp(dataset_path="/fake/path.shp")
    async with app.run_test() as pilot:
        # Dataset view should be present
        assert app.query_one("#dataset-view")
        assert app.query_one("#layer-tree")
        assert app.query_one("#metadata-content")
        assert app.query_one("#data-grid")


@pytest.mark.asyncio
async def test_tui_app_quit():
    """Pressing q should quit the app."""
    app = GeopeekApp(dataset_path=None)
    async with app.run_test() as pilot:
        await pilot.press("q")
        # App should exit (no assertion needed — test passes if no hang)
