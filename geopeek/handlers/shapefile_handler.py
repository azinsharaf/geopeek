from pathlib import Path
from typing import Generator, List, Dict, Any, Optional

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

    def _resolve_shapefile(self, layer_name: Optional[str] = None) -> Optional[Path]:
        """Resolve a single shapefile path, optionally by layer name."""
        shp_files = self._find_shapefiles()
        if not shp_files:
            return None
        if layer_name:
            for shp in shp_files:
                if shp.stem == layer_name:
                    return shp
            return None
        return shp_files[0]

    def _open_layer(self, shp_path: Path):
        """Open a shapefile and return (datasource, layer). Caller must close ds."""
        from osgeo import ogr

        ds = ogr.Open(str(shp_path), 0)
        if ds is None:
            return None, None
        layer = ds.GetLayerByIndex(0)
        return ds, layer

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
                crs_name = srs.GetName()
                info["crs"] = f"EPSG:{epsg} - {crs_name}" if epsg else crs_name
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
        }

        if not shp_files:
            return info

        # A single .shp is always one layer — flatten its metadata to the top level
        if len(shp_files) == 1:
            try:
                detail = self._get_layer_detail(shp_files[0])
            except Exception:
                detail = {"name": shp_files[0].stem, "error": "Failed to read"}
            # Merge layer detail into top-level info, skip redundant 'name'
            for key, val in detail.items():
                if key != "name":
                    info[key] = val
            return info

        # Multiple shapefiles in a directory — show as layers
        info["layer_count"] = len(shp_files)
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

    def get_schema(self, layer_name: Optional[str] = None) -> Dict[str, Any]:
        """Return field schema for a shapefile."""
        shp_path = self._resolve_shapefile(layer_name)
        if shp_path is None:
            return {
                "error": f"Layer not found: {layer_name}"
                if layer_name
                else "No shapefile found"
            }

        try:
            from osgeo import ogr
        except ImportError:
            return {"error": "GDAL Python bindings not available"}

        ds, layer = self._open_layer(shp_path)
        if ds is None or layer is None:
            return {"error": "Could not open with GDAL/OGR"}

        try:
            layer_defn = layer.GetLayerDefn()
            fields = []
            for j in range(layer_defn.GetFieldCount()):
                fd = layer_defn.GetFieldDefn(j)
                # Alias — shapefiles use the same name as alias (no alias support in DBF)
                try:
                    alias = fd.GetAlternativeNameRef() or ""
                except Exception:
                    alias = ""
                fields.append(
                    {
                        "name": fd.GetName(),
                        "alias": alias,
                        "type": fd.GetTypeName(),
                        "width": fd.GetWidth(),
                        "precision": fd.GetPrecision(),
                        "nullable": bool(fd.IsNullable()),
                    }
                )
            return {
                "layer": shp_path.stem,
                "geometry_type": ogr.GeometryTypeToName(layer.GetGeomType()),
                "field_count": len(fields),
                "fields": fields,
            }
        finally:
            ds = None

    def get_extent(self, layer_name: Optional[str] = None) -> Dict[str, Any]:
        """Return bounding box extent for a shapefile."""
        shp_path = self._resolve_shapefile(layer_name)
        if shp_path is None:
            return {
                "error": f"Layer not found: {layer_name}"
                if layer_name
                else "No shapefile found"
            }

        try:
            from osgeo import ogr
        except ImportError:
            return {"error": "GDAL Python bindings not available"}

        ds, layer = self._open_layer(shp_path)
        if ds is None or layer is None:
            return {"error": "Could not open with GDAL/OGR"}

        try:
            result: Dict[str, Any] = {"layer": shp_path.stem}

            # CRS
            srs = layer.GetSpatialRef()
            if srs:
                srs.AutoIdentifyEPSG()
                epsg = srs.GetAuthorityCode(None)
                crs_name = srs.GetName()
                result["crs"] = f"EPSG:{epsg} - {crs_name}" if epsg else crs_name
            else:
                result["crs"] = None

            # Extent
            try:
                extent = layer.GetExtent()
                result["extent"] = {
                    "xmin": extent[0],
                    "xmax": extent[1],
                    "ymin": extent[2],
                    "ymax": extent[3],
                }
            except Exception:
                result["extent"] = None

            return result
        finally:
            ds = None

    def peek(self, limit: int = 10, layer_name: Optional[str] = None) -> Dict[str, Any]:
        """Return a preview of attribute rows from the shapefile."""
        shp_path = self._resolve_shapefile(layer_name)
        if shp_path is None:
            return {
                "error": f"Layer not found: {layer_name}"
                if layer_name
                else "No shapefile found"
            }

        try:
            from osgeo import ogr
        except ImportError:
            return {"error": "GDAL Python bindings not available"}

        ds, layer = self._open_layer(shp_path)
        if ds is None or layer is None:
            return {"error": "Could not open with GDAL/OGR"}

        try:
            layer_defn = layer.GetLayerDefn()
            field_names = [
                layer_defn.GetFieldDefn(j).GetName()
                for j in range(layer_defn.GetFieldCount())
            ]

            rows = []
            layer.ResetReading()
            for _ in range(limit):
                feat = layer.GetNextFeature()
                if feat is None:
                    break
                row = {"FID": feat.GetFID()}
                for fname in field_names:
                    row[fname] = feat.GetField(fname)
                # Geometry type as a summary column
                geom = feat.GetGeometryRef()
                if geom:
                    row["geometry"] = geom.GetGeometryName()
                rows.append(row)

            total = layer.GetFeatureCount()
            return {
                "layer": shp_path.stem,
                "total_features": total,
                "showing": len(rows),
                "columns": ["FID"] + field_names + ["geometry"],
                "rows": rows,
            }
        finally:
            ds = None

    def iter_rows(
        self,
        layer_name: Optional[str] = None,
        skip: int = 0,
    ) -> Generator[Dict[str, Any], None, None]:
        """Yield every feature row as a dict, starting from *skip*.

        Designed for progressive loading: the caller controls chunking.
        Uses ``SetNextByIndex`` for O(1) seek; falls back to iterating
        past *skip* rows if the driver does not support random access.
        """
        shp_path = self._resolve_shapefile(layer_name)
        if shp_path is None:
            return

        try:
            from osgeo import ogr
        except ImportError:
            return

        ds, layer = self._open_layer(shp_path)
        if ds is None or layer is None:
            return

        try:
            layer_defn = layer.GetLayerDefn()
            field_names = [
                layer_defn.GetFieldDefn(j).GetName()
                for j in range(layer_defn.GetFieldCount())
            ]

            # Position cursor at `skip`
            if skip > 0:
                try:
                    layer.SetNextByIndex(skip)
                except Exception:
                    layer.ResetReading()
                    for _ in range(skip):
                        if layer.GetNextFeature() is None:
                            return
            else:
                layer.ResetReading()

            while True:
                feat = layer.GetNextFeature()
                if feat is None:
                    break
                row: Dict[str, Any] = {"FID": feat.GetFID()}
                for fname in field_names:
                    row[fname] = feat.GetField(fname)
                geom = feat.GetGeometryRef()
                if geom:
                    row["geometry"] = geom.GetGeometryName()
                yield row
        finally:
            ds = None
