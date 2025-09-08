import rasterio
from .base import BaseHandler

class RasterHandler(BaseHandler):
    @staticmethod
    def can_open(path: str) -> bool:
        return path.lower().endswith((".tif", ".tiff"))

    @staticmethod
    def info(path: str) -> dict:
        with rasterio.open(path) as src:
            return {
                "type": "raster",
                "driver": src.driver,
                "bands": src.count,
                "crs": src.crs.to_string() if src.crs else "Unknown",
                "extent": src.bounds,
                "resolution": src.res,
                "dtype": src.dtypes[0]
            }
