import os
import subprocess
from typing import Dict, Any, List

from .handler import Handler


class GDBHandler(Handler):
    """
    Handler for Esri File Geodatabase (.gdb) directories.
    Provides basic metadata and attempts to enumerate layers via ogrinfo if available.
    """

    def __init__(self, input_file: str):
        super().__init__(input_file)
        self.input_file = input_file
        self.exists = os.path.exists(self.input_file)
        self.is_dir = os.path.isdir(self.input_file)
        self.name = os.path.basename(self.input_file.rstrip(os.sep)) if self.input_file else ""
        self.size = self._compute_size(self.input_file) if self.exists else 0
        self.layers: List[str] = []

        # Try to populate layers if possible
        if self.exists:
            self.layers = self._detect_layers()

    def _compute_size(self, path: str) -> int:
        total = 0
        if os.path.isfile(path):
            return os.path.getsize(path)
        for root, _, files in os.walk(path):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
        return total

    def _detect_layers(self) -> List[str]:
        layers: List[str] = []
        # Attempt to use ogrinfo to enumerate layers inside the gdb
        try:
            result = subprocess.run(
                ["ogrinfo", "-ro", self.input_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15,
            )
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.splitlines():
                    line = line.strip()
                    # Typical ogrinfo output contains lines like:
                    # "Layer: <name>"
                    if line.lower().startswith("layer:"):
                        name = line.split(":", 1)[1].strip()
                        if name:
                            layers.append(name)
        except Exception:
            # If ogrinfo isn't available or any error occurs, fall back to empty list
            pass

        return layers

    def get_info(self) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "type": "gdb",
            "path": self.input_file,
            "name": self.name,
            "exists": self.exists,
            "size": self.size,
            "layers": self.layers,
        }

        # If path doesn't exist or isn't a directory, return early
        if not self.exists:
            return info

        # Optionally, attempt to enrich with a simple check if the path is a .gdb directory
        if self.is_dir:
            # Quick heuristic: Esri GDB directories contain a file named "metadata.sde" or many internal files.
            # We avoid false positives; just keep existing info.
            pass

        return info
