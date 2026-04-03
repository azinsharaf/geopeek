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


def _patch_handler(monkeypatch):
    monkeypatch.setattr(
        cli_module, "_select_handler", lambda input_file: DummyHandler()
    )


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


def test_cli_no_subcommand():
    runner = CliRunner()
    result = runner.invoke(cli_module.app, [])
    assert result.exit_code == 1
