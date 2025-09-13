from typer.testing import CliRunner
from geopeek import cli as cli_module

def test_cli_info_invocation(monkeypatch):
    class DummyHandler:
        def get_info(self):
            return {
                "type": "gdb",
                "path": "/path/to/dataset.gdb",
                "name": "dataset",
                "exists": True,
                "size": 0,
                "layers": ["layer1", "layer2"],
            }

    runner = CliRunner()
    # Patch internal selector to return our dummy handler
    monkeypatch.setattr(cli_module, "_select_handler", lambda input_file: DummyHandler())
    result = runner.invoke(cli_module.app, ["info", "/path/to/dataset.gdb"])
    assert result.exit_code == 0
    # Ensure the CLI printed the Information title
    assert "Information" in result.output
    # Optional: ensure layers show up in output via the printer
    assert "layer1" in result.output
    assert "layer2" in result.output
