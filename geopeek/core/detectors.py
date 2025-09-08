def detect_file_type(path: str) -> str:
    """Detect the file type based on the extension."""
    if path.lower().endswith(".shp"):
        return "shapefile"
    elif path.lower().endswith((".tif", ".tiff")):
        return "raster"
    else:
        return "unknown"
