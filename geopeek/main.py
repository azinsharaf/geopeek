class GeoPeek:
    def __init__(self, gdb_path: str):
        self.gdb_path = gdb_path

    def list_feature_classes(self):
        handlers = {
            "shapefile": ShapefileHandler,
            "raster": RasterHandler
        }

        file_type = detect_file_type(self.gdb_path)
        if file_type in handlers:
            handler_class = handlers[file_type]
            try:
                handler = handler_class()
                return handler.info(self.gdb_path)
            except Exception as e:
                print(f"Error listing feature classes: {e}")
                return []
        else:
            print(f"Unsupported file type: {file_type}")
            return []
