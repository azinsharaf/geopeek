import os
from typing import Dict, Any, List

from .handler import Handler


class GDBHandler(Handler):
    """
    Handler for Esri File Geodatabase (.gdb) directories.
    Uses GDAL/OGR Python bindings for layer enumeration and metadata.
    """

    def __init__(self, input_file: str):
        super().__init__(input_file)
        self.input_file = input_file

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

    def _human_readable_size(self, size_bytes: int) -> str:
        if size_bytes < 0:
            return "0 B"
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}" if unit != "B" else f"{size_bytes} B"
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"

    def _get_layer_details(self, ds) -> List[Dict[str, Any]]:
        """Extract detailed info for each layer in the datasource."""
        from osgeo import ogr

        layers = []
        for i in range(ds.GetLayerCount()):
            layer = ds.GetLayerByIndex(i)
            if layer is None:
                continue

            layer_info: Dict[str, Any] = {
                "name": layer.GetName(),
                "feature_count": layer.GetFeatureCount(),
                "geometry_type": ogr.GeometryTypeToName(layer.GetGeomType()),
            }

            # Extent
            try:
                extent = layer.GetExtent()
                layer_info["extent"] = {
                    "xmin": extent[0],
                    "xmax": extent[1],
                    "ymin": extent[2],
                    "ymax": extent[3],
                }
            except Exception:
                layer_info["extent"] = None

            # CRS
            srs = layer.GetSpatialRef()
            if srs:
                srs.AutoIdentifyEPSG()
                epsg = srs.GetAuthorityCode(None)
                crs_name = srs.GetName()
                layer_info["crs"] = f"EPSG:{epsg} - {crs_name}" if epsg else crs_name
            else:
                layer_info["crs"] = None

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
            layer_info["fields"] = fields

            layers.append(layer_info)
        return layers

    def get_info(self) -> Dict[str, Any]:
        exists = os.path.exists(self.input_file)
        name = (
            os.path.basename(self.input_file.rstrip(os.sep)) if self.input_file else ""
        )

        info: Dict[str, Any] = {
            "type": "File Geodatabase",
            "path": self.input_file,
            "name": name,
            "exists": exists,
        }

        if not exists:
            info["size"] = "0 B"
            info["layer_count"] = 0
            info["layers"] = []
            return info

        size_bytes = self._compute_size(self.input_file)
        info["size"] = self._human_readable_size(size_bytes)

        try:
            from osgeo import ogr
        except ImportError:
            info["layer_count"] = 0
            info["layers"] = []
            info["error"] = "GDAL Python bindings not available"
            return info

        ds = ogr.Open(self.input_file, 0)
        if ds is None:
            info["layer_count"] = 0
            info["layers"] = []
            info["error"] = "Could not open dataset with GDAL/OGR"
            return info

        try:
            info["layer_count"] = ds.GetLayerCount()
            info["layers"] = self._get_layer_details(ds)
        finally:
            ds = None  # close dataset

        return info

    def get_layers(self) -> List[str]:
        """Return just the layer names (for --layers flag)."""
        try:
            from osgeo import ogr
        except ImportError:
            return []

        ds = ogr.Open(self.input_file, 0)
        if ds is None:
            return []
        try:
            return [
                ds.GetLayerByIndex(i).GetName()
                for i in range(ds.GetLayerCount())
                if ds.GetLayerByIndex(i) is not None
            ]
        finally:
            ds = None
