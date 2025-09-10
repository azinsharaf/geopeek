
from pathlib import Path
from typing import List, Dict, Any

from .handler import Handler


class RasterHandler(Handler):
    """
    Handler for raster datasets. Supports single raster files or directories containing raster files.
    Detects raster layers by common raster file extensions.
    """
    _RASTER_EXTS = {".tif", ".tiff", ".img", ".vrt", ".nc", ".grd", ".bil", ".asc"}

    def __init__(self, input_file: str):
        super().__init__(input_file)
        self.input_file = input_file

    def _compute_size(self, path: str) -> int:
        p = Path(path)
        if p.is_dir():
            total = 0
            for f in p.rglob('*'):
                if f.is_file():
                    try:
                        total += f.stat().st_size
                    except OSError:
                        pass
            return total
        elif p.is_file():
            try:
                return p.stat().st_size
            except OSError:
                return 0
        else:
            return 0

    def _detect_layers(self) -> List[str]:
        layers: List[str] = []
        p = Path(self.input_file)

        if p.is_dir():
            for f in sorted(p.glob('*')):
                if f.is_file() and f.suffix.lower() in self._RASTER_EXTS:
                    layers.append(f.stem)
        elif p.is_file() and p.suffix.lower() in self._RASTER_EXTS:
            layers.append(p.stem)

        return layers

    def get_info(self) -> Dict[str, Any]:
        return {
            "type": "Raster",
            "path": str(self.input_file),
            "size": self._compute_size(self.input_file),
            "layers": self._detect_layers(),
        }
