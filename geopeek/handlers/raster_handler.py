from pathlib import Path
from typing import List, Dict, Any, Optional

from .handler import Handler


class RasterHandler(Handler):
    """
    Handler for raster datasets. Uses GDAL Python bindings for metadata extraction.
    """

    _RASTER_EXTS = {
        ".tif",
        ".tiff",
        ".img",
        ".vrt",
        ".nc",
        ".grd",
        ".bil",
        ".asc",
        ".jp2",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".dem",
    }

    def __init__(self, input_file: str):
        super().__init__(input_file)
        self.input_file = input_file

    def _human_readable_size(self, size_bytes: int) -> str:
        if size_bytes < 0:
            return "0 B"
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}" if unit != "B" else f"{size_bytes} B"
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"

    def _compute_size(self, path: str) -> int:
        p = Path(path)
        if p.is_dir():
            total = 0
            for f in p.rglob("*"):
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
        return 0

    def _find_raster_path(self) -> Optional[str]:
        """Resolve the path to the raster file to open."""
        p = Path(self.input_file)
        if p.is_file():
            return str(p)
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.suffix.lower() in self._RASTER_EXTS:
                    return str(f)
        return None

    def _detect_layers(self) -> List[str]:
        p = Path(self.input_file)
        if p.is_dir():
            return [
                f.stem
                for f in sorted(p.glob("*"))
                if f.is_file() and f.suffix.lower() in self._RASTER_EXTS
            ]
        elif p.is_file() and p.suffix.lower() in self._RASTER_EXTS:
            return [p.stem]
        return []

    def _get_raster_detail(self, ds) -> Dict[str, Any]:
        """Extract detailed raster metadata from an open GDAL dataset."""
        from osgeo import gdal, osr

        detail: Dict[str, Any] = {}

        # Dimensions
        detail["columns"] = ds.RasterXSize
        detail["rows"] = ds.RasterYSize
        detail["band_count"] = ds.RasterCount

        # GeoTransform and cell size
        gt = ds.GetGeoTransform()
        if gt:
            cell_x = abs(gt[1])
            cell_y = abs(gt[5])
            detail["cell_size_x"] = cell_x
            detail["cell_size_y"] = cell_y
            detail["origin_x"] = gt[0]
            detail["origin_y"] = gt[3]

        # Extent
        if gt:
            xmin = gt[0]
            ymax = gt[3]
            xmax = xmin + gt[1] * ds.RasterXSize
            ymin = ymax + gt[5] * ds.RasterYSize
            detail["extent"] = {
                "xmin": xmin,
                "xmax": xmax,
                "ymin": ymin,
                "ymax": ymax,
            }

        # CRS
        proj = ds.GetProjection()
        if proj:
            srs = osr.SpatialReference()
            srs.ImportFromWkt(proj)
            srs.AutoIdentifyEPSG()
            epsg = srs.GetAuthorityCode(None)
            crs_name = srs.GetName()
            detail["crs"] = f"EPSG:{epsg} - {crs_name}" if epsg else crs_name

            # Units
            if srs.IsProjected():
                detail["linear_unit"] = srs.GetLinearUnitsName()
            elif srs.IsGeographic():
                detail["angular_unit"] = srs.GetAngularUnitsName()
        else:
            detail["crs"] = None

        # Band info
        bands = []
        for i in range(1, ds.RasterCount + 1):
            band = ds.GetRasterBand(i)
            if band is None:
                continue
            band_info = {
                "band": i,
                "data_type": gdal.GetDataTypeName(band.DataType),
                "nodata": band.GetNoDataValue(),
            }
            stats = band.GetStatistics(True, False)
            if stats and stats != [0, 0, 0, 0]:
                band_info["min"] = stats[0]
                band_info["max"] = stats[1]
                band_info["mean"] = stats[2]
                band_info["stddev"] = stats[3]
            bands.append(band_info)
        detail["bands"] = bands

        # Driver
        driver = ds.GetDriver()
        if driver:
            detail["driver"] = driver.ShortName

        return detail

    def get_info(self) -> Dict[str, Any]:
        size_bytes = self._compute_size(self.input_file)
        raster_path = self._find_raster_path()

        info: Dict[str, Any] = {
            "type": "Raster",
            "path": str(self.input_file),
            "size": self._human_readable_size(size_bytes),
            "layers": self._detect_layers(),
        }

        if raster_path is None:
            return info

        try:
            from osgeo import gdal
        except ImportError:
            info["error"] = "GDAL Python bindings not available"
            return info

        ds = gdal.Open(raster_path, gdal.GA_ReadOnly)
        if ds is None:
            info["error"] = "Could not open dataset with GDAL"
            return info

        try:
            detail = self._get_raster_detail(ds)
            info.update(detail)
        finally:
            ds = None

        return info

    def get_layers(self) -> List[str]:
        """Return just the layer/file names."""
        return self._detect_layers()
