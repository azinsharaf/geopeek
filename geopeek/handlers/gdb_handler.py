from geopeek.core.detectors import Detector  # Added this line

class GDBHandler:
    def __init__(self, input_file):
        self.input_file = input_file
        self.detector = Detector(input_file)

    def print_info(self):
        metadata = self.detector.get_metadata()
        print_rich_table(metadata, "Metadata")

    def print_gdb_info(self):
        gdb_info = self.detector.get_gdb_info()
        print_rich_table(gdb_info, "Geodatabase Information")
