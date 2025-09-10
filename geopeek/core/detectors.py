class Detector:
    def __init__(self, input_file):
        self.input_file = input_file


    def get_gdb_info(self):
        # Get Geodatabase information
        gdb_info = {
            "Database Name": self.input_file,
            "Feature Classes": ["feature_class1", "feature_class2"],
            "Tables": ["table1", "table2"]
        }
        return gdb_info

    def get_raster_info(self):
        # Get Raster information
        raster_info = {
            "Raster File": self.input_file,
            "Spatial Reference System": "EPSG:4326",
            "Resolution": [10, 10]
        }
        return raster_info
