"""Tests for geopeek handlers.

Note: Tests that use GDAL to open actual shapefiles require GDAL to be
installed. Tests that only check file detection / size computation work
without GDAL.
"""

import pytest
from unittest.mock import patch, MagicMock
from geopeek.handlers.shapefile_handler import ShapefileHandler
from geopeek.handlers.gdb_handler import GDBHandler
from geopeek.handlers.raster_handler import RasterHandler


# --- ShapefileHandler tests ---


def test_shapefile_handler_detects_shp_in_directory(tmp_path):
    (tmp_path / "a.shp").write_text("data")
    (tmp_path / "b.shp").write_text("data2")
    handler = ShapefileHandler(str(tmp_path))
    layers = handler.get_layers()
    assert layers == ["a", "b"]


def test_shapefile_handler_detects_single_file(tmp_path):
    f = tmp_path / "myshape.shp"
    f.write_text("abc")
    handler = ShapefileHandler(str(f))
    layers = handler.get_layers()
    assert layers == ["myshape"]


def test_shapefile_handler_nonexistent_path():
    handler = ShapefileHandler("/does/not/exist")
    info = handler.get_info()
    assert info["path"] == "/does/not/exist"
    assert info["type"] == "Shapefile"
    # No shapefiles found — no layer keys
    assert "layers" not in info
    assert "layer_count" not in info


def test_shapefile_handler_single_file_flattened(tmp_path):
    """Single .shp should flatten layer metadata to top level."""
    f = tmp_path / "test.shp"
    f.write_text("dummy")
    handler = ShapefileHandler(str(f))
    info = handler.get_info()
    assert info["type"] == "Shapefile"
    assert info["path"] == str(f)
    assert "size" in info
    # Single shapefile: layer detail is flattened, no 'layers' list
    assert "layers" not in info
    assert "layer_count" not in info


# --- GDBHandler tests ---


def test_gdb_handler_nonexistent_path():
    handler = GDBHandler("/does/not/exist.gdb")
    info = handler.get_info()
    assert info["exists"] is False
    assert info["layer_count"] == 0
    assert info["layers"] == []


def test_gdb_handler_get_info_structure(tmp_path):
    gdb = tmp_path / "test.gdb"
    gdb.mkdir()
    (gdb / "dummy.gdbtable").write_text("data")
    handler = GDBHandler(str(gdb))
    info = handler.get_info()
    assert info["type"] == "File Geodatabase"
    assert info["name"] == "test.gdb"
    assert info["exists"] is True
    assert "size" in info


# --- RasterHandler tests ---


def test_raster_handler_nonexistent_path():
    handler = RasterHandler("/does/not/exist.tif")
    info = handler.get_info()
    assert info["type"] == "Raster"
    assert info["path"] == "/does/not/exist.tif"


def test_raster_handler_detect_layers_in_directory(tmp_path):
    (tmp_path / "dem.tif").write_text("raster")
    (tmp_path / "ortho.tif").write_text("raster")
    (tmp_path / "notes.txt").write_text("text")
    handler = RasterHandler(str(tmp_path))
    layers = handler.get_layers()
    assert "dem" in layers
    assert "ortho" in layers
    assert "notes" not in layers


def test_raster_handler_detect_single_file(tmp_path):
    f = tmp_path / "elevation.tif"
    f.write_text("raster")
    handler = RasterHandler(str(f))
    assert handler.get_layers() == ["elevation"]


# --- Human readable size tests ---


def test_human_readable_size():
    handler = RasterHandler("/dummy.tif")
    assert handler._human_readable_size(0) == "0 B"
    assert handler._human_readable_size(1023) == "1023 B"
    assert "KB" in handler._human_readable_size(1024)
    assert "MB" in handler._human_readable_size(1024 * 1024)
    assert "GB" in handler._human_readable_size(1024 * 1024 * 1024)
