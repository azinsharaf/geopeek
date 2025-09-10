import pytest
from geopeek.handlers import ShapefileHandler


def test_shapefile_handler_directory(tmp_path):
    p = tmp_path
    (p / "a.shp").write_text("data")
    handler = ShapefileHandler(str(p))
    info = handler.get_info()
    assert info["type"] == "Shapefile"
    assert info["path"] == str(p)
    assert info["layers"] == ["a"]
    assert info["size"] == (p / "a.shp").stat().st_size


def test_shapefile_handler_single_file(tmp_path):
    f = tmp_path / "myshape.shp"
    f.write_text("abc")
    handler = ShapefileHandler(str(f))
    info = handler.get_info()
    assert info["type"] == "Shapefile"
    assert info["path"] == str(f)
    assert info["layers"] == ["myshape"]
    assert info["size"] == 3


def test_shapefile_handler_multiple_shp_in_dir(tmp_path):
    p = tmp_path
    (p / "aaa.shp").write_text("x")
    (p / "bbb.shp").write_text("yy")
    handler = ShapefileHandler(str(p))
    info = handler.get_info()
    assert info["layers"] == ["aaa", "bbb"]


def test_shapefile_handler_nonexistent_path():
    handler = ShapefileHandler("/does/not/exist")
    info = handler.get_info()
    assert info["path"] == "/does/not/exist"
    assert info["size"] == 0
    assert info["layers"] == []
    assert info["type"] == "Shapefile"
