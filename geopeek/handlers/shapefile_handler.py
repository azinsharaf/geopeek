from pathlib import Path
from typing import List, Dict, Any

from .handler import Handler


class ShapefileHandler(Handler):
    """
    Handler for Esri Shapefiles (.shp) or directories containing shapefiles.
    Uses GDAL/OGR Python bindings for metadata extraction.
    """

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
        path_obj = Path(path)
        if path_obj.is_dir():
            total = 0
            for p in path_obj.rglob("*"):
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
        return 0

    def _find_shapefiles(self) -> List[Path]:
        """Find all .shp files to inspect."""
        p = Path(self.input_file)
        if p.is_dir():
            return sorted(p.glob("*.shp"))
        elif p.is_file() and p.suffix.lower() == ".shp":
            return [p]
        return []

    def _get_layer_detail(self, shp_path: Path) -> Dict[str, Any]:
        """Extract detailed metadata from a single shapefile using OGR."""
        from osgeo import ogr

        ds = ogr.Open(str(shp_path), 0)
        if ds is None:
            return {
                "name": shp_path.stem,
                "error": "Could not open with GDAL/OGR",
            }

        try:
            layer = ds.GetLayerByIndex(0)
            if layer is None:
                return {"name": shp_path.stem, "error": "No layer found"}

            info: Dict[str, Any] = {
                "name": layer.GetName(),
                "feature_count": layer.GetFeatureCount(),
                "geometry_type": ogr.GeometryTypeToName(layer.GetGeomType()),  # noqa: F821
            }

            # Extent
            try:
                extent = layer.GetExtent()
                info["extent"] = {
                    "xmin": extent[0],
                    "xmax": extent[1],
                    "ymin": extent[2],
                    "ymax": extent[3],
                }
            except Exception:
                info["extent"] = None

            # CRS
            srs = layer.GetSpatialRef()
            if srs:
                srs.AutoIdentifyEPSG()
                epsg = srs.GetAuthorityCode(None)
                info["crs"] = f"EPSG:{epsg}" if epsg else srs.GetName()
            else:
                info["crs"] = None

            # Fields
            layer_defn = layer.GetLayerDefn()
            fields = []
            for j in range(layer_defn.GetFieldCount()):
                field_defn = layer_defn.GetFieldDefn(j)
                fields.append(
                    {
                        "name": field_defn.GetName(),
                        "type": field_defn.GetTypeName(),
                        "width": field_defn.GetWidth(),
                    }
                )
            info["fields"] = fields

            return info
        finally:
            ds = None

    def get_info(self) -> Dict[str, Any]:
        shp_files = self._find_shapefiles()
        size_bytes = self._compute_size(self.input_file)

        info: Dict[str, Any] = {
            "type": "Shapefile",
            "path": str(self.input_file),
            "size": self._human_readable_size(size_bytes),
            "layer_count": len(shp_files),
        }

        if not shp_files:
            info["layers"] = []
            return info

        layers = []
        for shp in shp_files:
            try:
                layers.append(self._get_layer_detail(shp))
            except Exception:
                layers.append({"name": shp.stem, "error": "Failed to read"})
        info["layers"] = layers

        return info

    def get_layers(self) -> List[str]:
        """Return just the layer names."""
        return [shp.stem for shp in self._find_shapefiles()]
