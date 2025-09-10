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
