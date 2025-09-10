
from pathlib import Path
from typing import List, Dict, Any

from .handler import Handler


class ShapefileHandler(Handler):
    """
    Handler for Esri Shapefiles (.shp) or directories containing shapefile components.
    Provides basic metadata and detects available shapefile layers present in the dataset.
    """

    def __init__(self, input_file: str):
        super().__init__(input_file)
        self.input_file = input_file

    def _compute_size(self, path: str) -> int:
        path_obj = Path(path)
        if path_obj.is_dir():
            total = 0
            for p in path_obj.rglob('*'):
                if p.is_file():
                    try:
                        total += p.stat().st_size
                    except OSError:
                        pass
            return total
        elif path_obj.is_file():
            try:
                return path_obj.stat().st_size
            except OSError:
                return 0
        else:
            return 0

    def _detect_layers(self) -> List[str]:
        layers: List[str] = []
        p = Path(self.input_file)

        if p.is_dir():
            for shp in sorted(p.glob('*.shp')):
                layers.append(shp.stem)
        elif p.is_file() and p.suffix.lower() == '.shp':
            layers.append(p.stem)

        return layers

    def get_info(self) -> Dict[str, Any]:
        return {
            "type": "Shapefile",
            "path": str(self.input_file),
            "size": self._compute_size(self.input_file),
            "layers": self._detect_layers(),
        }
