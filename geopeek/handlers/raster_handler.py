
from pathlib import Path
from typing import List, Dict, Any, Optional

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

    def _human_readable_size(self, size_bytes: int) -> str:
        """
        Convert size in bytes to a human-readable string using MB or GB.
        """
        if size_bytes is None or size_bytes < 0:
            return "0 MB"
        mb = size_bytes / (1024 * 1024)
        if mb >= 1024:
            gb = mb / 1024
            return f"{gb:.2f} GB"
        else:
            return f"{mb:.2f} MB"

    def _detect_cell_size(self) -> Optional[float]:
        """
        Attempt to detect the raster cell size using rasterio if available.
        Returns average of the pixel width and height in map units, or None if unavailable.
        """
        try:
            from rasterio import open as rio_open
            p = Path(self.input_file)
            if p.is_file():
                with rio_open(str(p)) as src:
                    t = src.transform
                    w = abs(t.a)
                    h = abs(t.e)
                    if w == 0 and h == 0:
                        return None
                    return (w + h) / 2.0
        except Exception:
            pass
        return None

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
        size_bytes = self._compute_size(self.input_file)
        return {
            "type": "Raster",
            "path": str(self.input_file),
            "size": size_bytes,
            "size_readable": self._human_readable_size(size_bytes),
            "cell_size": self._detect_cell_size(),
            "layers": self._detect_layers(),
        }
