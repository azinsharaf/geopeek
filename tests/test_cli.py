import json
from typer.testing import CliRunner
from geopeek import cli as cli_module


class DummyHandler:
    def get_info(self):
        return {
            "type": "File Geodatabase",
            "path": "/path/to/dataset.gdb",
            "name": "dataset",
            "exists": True,
            "size": "1.50 MB",
            "layer_count": 2,
            "layers": [
                {"name": "layer1", "feature_count": 10, "geometry_type": "Point"},
                {"name": "layer2", "feature_count": 20, "geometry_type": "Polygon"},
            ],
        }

    def get_layers(self):
        return ["layer1", "layer2"]

    def get_schema(self, layer_name=None):
        if layer_name:
            return {
                "layer": layer_name,
                "geometry_type": "Point",
                "field_count": 2,
                "fields": [
                    {"name": "id", "type": "Integer", "width": 10, "precision": 0},
                    {"name": "name", "type": "String", "width": 50, "precision": 0},
                ],
            }
        return {
            "layer_count": 2,
            "schemas": [
                {
                    "layer": "layer1",
                    "geometry_type": "Point",
                    "field_count": 1,
                    "fields": [
                        {"name": "id", "type": "Integer", "width": 10, "precision": 0},
                    ],
                },
                {
                    "layer": "layer2",
                    "geometry_type": "Polygon",
                    "field_count": 1,
                    "fields": [
                        {"name": "name", "type": "String", "width": 50, "precision": 0},
                    ],
                },
            ],
        }

    def get_extent(self, layer_name=None):
        if layer_name:
            return {
                "layer": layer_name,
                "crs": "EPSG:4326 - WGS 84",
                "extent": {"xmin": -180.0, "xmax": 180.0, "ymin": -90.0, "ymax": 90.0},
            }
        return {
            "layer_count": 2,
            "extents": [
                {
                    "layer": "layer1",
                    "crs": "EPSG:4326 - WGS 84",
                    "extent": {
                        "xmin": -180.0,
                        "xmax": 180.0,
                        "ymin": -90.0,
                        "ymax": 90.0,
                    },
                },
                {
                    "layer": "layer2",
                    "crs": "EPSG:4326 - WGS 84",
                    "extent": {"xmin": 0.0, "xmax": 10.0, "ymin": 0.0, "ymax": 10.0},
                },
            ],
        }

    def peek(self, limit=10, layer_name=None):
        return {
            "layer": layer_name or "layer1",
            "total_features": 100,
            "showing": min(limit, 3),
            "columns": ["FID", "id", "name", "geometry"],
            "rows": [
                {"FID": 0, "id": 1, "name": "Alpha", "geometry": "POINT"},
                {"FID": 1, "id": 2, "name": "Beta", "geometry": "POINT"},
                {"FID": 2, "id": 3, "name": "Gamma", "geometry": "POINT"},
            ][: min(limit, 3)],
        }


def _patch_handler(monkeypatch):
    monkeypatch.setattr(
        cli_module, "_select_handler", lambda input_file: DummyHandler()
    )


# --- info command tests ---


def test_cli_info_table_output(monkeypatch):
    _patch_handler(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli_module.app, ["info", "/path/to/dataset.gdb"])
    assert result.exit_code == 0
    assert "Information" in result.output
    assert "layer1" in result.output
    assert "layer2" in result.output


def test_cli_info_json_output(monkeypatch):
    _patch_handler(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(
        cli_module.app, ["info", "/path/to/dataset.gdb", "--format", "json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["type"] == "File Geodatabase"
    assert data["layer_count"] == 2


def test_cli_layers_flag(monkeypatch):
    _patch_handler(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli_module.app, ["info", "/path/to/dataset.gdb", "--layers"])
    assert result.exit_code == 0
    assert "layer1" in result.output
    assert "layer2" in result.output


def test_cli_layers_json_flag(monkeypatch):
    _patch_handler(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(
        cli_module.app, ["info", "/path/to/dataset.gdb", "--layers", "--format", "json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["layers"] == ["layer1", "layer2"]


# --- peek command tests ---


def test_cli_peek_table_output(monkeypatch):
    _patch_handler(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli_module.app, ["peek", "/path/to/dataset.gdb"])
    assert result.exit_code == 0
    assert "Preview" in result.output
    assert "Alpha" in result.output
    assert "Beta" in result.output


def test_cli_peek_json_output(monkeypatch):
    _patch_handler(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(
        cli_module.app, ["peek", "/path/to/dataset.gdb", "--format", "json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["total_features"] == 100
    assert len(data["rows"]) == 3


def test_cli_peek_with_limit(monkeypatch):
    _patch_handler(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(
        cli_module.app,
        ["peek", "/path/to/dataset.gdb", "--limit", "2", "--format", "json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data["rows"]) == 2


def test_cli_peek_with_layer(monkeypatch):
    _patch_handler(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(
        cli_module.app,
        ["peek", "/path/to/dataset.gdb", "--layer", "layer2", "--format", "json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["layer"] == "layer2"


# --- schema command tests ---


def test_cli_schema_table_output(monkeypatch):
    _patch_handler(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli_module.app, ["schema", "/path/to/dataset.gdb"])
    assert result.exit_code == 0
    assert "Schema" in result.output
    assert "layer1" in result.output


def test_cli_schema_json_output(monkeypatch):
    _patch_handler(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(
        cli_module.app, ["schema", "/path/to/dataset.gdb", "--format", "json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["layer_count"] == 2
    assert len(data["schemas"]) == 2


def test_cli_schema_with_layer(monkeypatch):
    _patch_handler(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(
        cli_module.app,
        ["schema", "/path/to/dataset.gdb", "--layer", "layer1", "--format", "json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["layer"] == "layer1"
    assert data["field_count"] == 2


# --- extent command tests ---


def test_cli_extent_table_output(monkeypatch):
    _patch_handler(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli_module.app, ["extent", "/path/to/dataset.gdb"])
    assert result.exit_code == 0
    assert "Extent" in result.output
    assert "layer1" in result.output


def test_cli_extent_json_output(monkeypatch):
    _patch_handler(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(
        cli_module.app, ["extent", "/path/to/dataset.gdb", "--format", "json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["layer_count"] == 2
    assert len(data["extents"]) == 2


def test_cli_extent_with_layer(monkeypatch):
    _patch_handler(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(
        cli_module.app,
        ["extent", "/path/to/dataset.gdb", "--layer", "layer1", "--format", "json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["layer"] == "layer1"
    assert data["extent"]["xmin"] == -180.0


# --- help shows new commands ---


def test_cli_help_shows_new_commands():
    runner = CliRunner()
    result = runner.invoke(cli_module.app, ["--help"])
    assert result.exit_code == 0
    assert "peek" in result.output
    assert "schema" in result.output
    assert "extent" in result.output


def test_cli_no_subcommand_launches_tui(monkeypatch):
    """Running geopeek with no args should launch the TUI."""
    launched = []
    monkeypatch.setattr(
        cli_module,
        "_launch_tui",
        lambda dataset_path=None: launched.append(dataset_path),
    )
    runner = CliRunner()
    result = runner.invoke(cli_module.app, [])
    assert result.exit_code == 0
    assert launched == [None]


def test_cli_browse_launches_tui(monkeypatch):
    """Running geopeek browse <path> should launch TUI on that dataset."""
    launched = []
    monkeypatch.setattr(
        cli_module,
        "_launch_tui",
        lambda dataset_path=None: launched.append(dataset_path),
    )
    runner = CliRunner()
    result = runner.invoke(cli_module.app, ["browse", "/path/to/data.gdb"])
    assert result.exit_code == 0
    assert launched == ["/path/to/data.gdb"]
