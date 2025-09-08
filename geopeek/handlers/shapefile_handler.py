import fiona
from .base import BaseHandler

class ShapefileHandler(BaseHandler):
    @staticmethod
    def can_open(path: str) -> bool:
        return path.lower().endswith(".shp")

    @staticmethod
    def info(path: str) -> dict:
        with fiona.open(path, "r") as src:
            return {
                "type": "vector",
                "driver": src.driver,
                "crs": src.crs.to_string() if src.crs else "Unknown",
                "features": len(src),
                "bounds": src.bounds,
                "layers": 1
            }
