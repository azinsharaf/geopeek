import os
from typing import Generator, Dict, Any, List, Optional

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

    def _open_datasource(self):
        """Open the GDB and return the OGR datasource, or None."""
        try:
            from osgeo import ogr
        except ImportError:
            return None
        try:
            return ogr.Open(self.input_file, 0)
        except RuntimeError:
            return None

    def _resolve_layer(self, ds, layer_name: Optional[str] = None):
        """Get a layer from the datasource by name, or the first layer."""
        if layer_name:
            layer = ds.GetLayerByName(layer_name)
            return layer
        if ds.GetLayerCount() > 0:
            return ds.GetLayerByIndex(0)
        return None

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

        try:
            ds = ogr.Open(self.input_file, 0)
        except RuntimeError:
            ds = None
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

        try:
            ds = ogr.Open(self.input_file, 0)
        except RuntimeError:
            return []
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

    def get_schema(self, layer_name: Optional[str] = None) -> Dict[str, Any]:
        """Return field schema for a GDB layer."""
        ds = self._open_datasource()
        if ds is None:
            return {"error": "Could not open dataset with GDAL/OGR"}

        try:
            from osgeo import ogr

            # If no layer specified and multiple layers, return all schemas
            if layer_name is None and ds.GetLayerCount() > 1:
                schemas = []
                for i in range(ds.GetLayerCount()):
                    layer = ds.GetLayerByIndex(i)
                    if layer is None:
                        continue
                    layer_defn = layer.GetLayerDefn()
                    fields = []
                    for j in range(layer_defn.GetFieldCount()):
                        fd = layer_defn.GetFieldDefn(j)
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
                    schemas.append(
                        {
                            "layer": layer.GetName(),
                            "geometry_type": ogr.GeometryTypeToName(
                                layer.GetGeomType()
                            ),
                            "field_count": len(fields),
                            "fields": fields,
                        }
                    )
                return {"layer_count": len(schemas), "schemas": schemas}

            layer = self._resolve_layer(ds, layer_name)
            if layer is None:
                return {
                    "error": f"Layer not found: {layer_name}"
                    if layer_name
                    else "No layers in dataset"
                }

            layer_defn = layer.GetLayerDefn()
            fields = []
            for j in range(layer_defn.GetFieldCount()):
                fd = layer_defn.GetFieldDefn(j)
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
                "layer": layer.GetName(),
                "geometry_type": ogr.GeometryTypeToName(layer.GetGeomType()),
                "field_count": len(fields),
                "fields": fields,
            }
        finally:
            ds = None

    def get_extent(self, layer_name: Optional[str] = None) -> Dict[str, Any]:
        """Return bounding box extent for a GDB layer."""
        ds = self._open_datasource()
        if ds is None:
            return {"error": "Could not open dataset with GDAL/OGR"}

        try:
            # If no layer specified and multiple layers, return all extents
            if layer_name is None and ds.GetLayerCount() > 1:
                extents = []
                for i in range(ds.GetLayerCount()):
                    layer = ds.GetLayerByIndex(i)
                    if layer is None:
                        continue
                    entry: Dict[str, Any] = {"layer": layer.GetName()}
                    srs = layer.GetSpatialRef()
                    if srs:
                        srs.AutoIdentifyEPSG()
                        epsg = srs.GetAuthorityCode(None)
                        crs_name = srs.GetName()
                        entry["crs"] = f"EPSG:{epsg} - {crs_name}" if epsg else crs_name
                    else:
                        entry["crs"] = None
                    try:
                        ext = layer.GetExtent()
                        entry["extent"] = {
                            "xmin": ext[0],
                            "xmax": ext[1],
                            "ymin": ext[2],
                            "ymax": ext[3],
                        }
                    except Exception:
                        entry["extent"] = None
                    extents.append(entry)
                return {"layer_count": len(extents), "extents": extents}

            layer = self._resolve_layer(ds, layer_name)
            if layer is None:
                return {
                    "error": f"Layer not found: {layer_name}"
                    if layer_name
                    else "No layers in dataset"
                }

            result: Dict[str, Any] = {"layer": layer.GetName()}
            srs = layer.GetSpatialRef()
            if srs:
                srs.AutoIdentifyEPSG()
                epsg = srs.GetAuthorityCode(None)
                crs_name = srs.GetName()
                result["crs"] = f"EPSG:{epsg} - {crs_name}" if epsg else crs_name
            else:
                result["crs"] = None

            try:
                ext = layer.GetExtent()
                result["extent"] = {
                    "xmin": ext[0],
                    "xmax": ext[1],
                    "ymin": ext[2],
                    "ymax": ext[3],
                }
            except Exception:
                result["extent"] = None

            return result
        finally:
            ds = None

    def peek(self, limit: int = 10, layer_name: Optional[str] = None) -> Dict[str, Any]:
        """Return a preview of attribute rows from a GDB layer."""
        ds = self._open_datasource()
        if ds is None:
            return {"error": "Could not open dataset with GDAL/OGR"}

        try:
            layer = self._resolve_layer(ds, layer_name)
            if layer is None:
                return {
                    "error": f"Layer not found: {layer_name}"
                    if layer_name
                    else "No layers in dataset"
                }

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
                geom = feat.GetGeometryRef()
                if geom:
                    row["geometry"] = geom.GetGeometryName()
                rows.append(row)

            total = layer.GetFeatureCount()
            return {
                "layer": layer.GetName(),
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
        ds = self._open_datasource()
        if ds is None:
            return

        try:
            layer = self._resolve_layer(ds, layer_name)
            if layer is None:
                return

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
