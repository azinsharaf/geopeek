import os
from fiona import collection

class GDBHandler:
    def __init__(self, input_file):
        self.input_file = input_file

    def get_feature_classes(self):
        # Use Fiona to read the file geodatabase and get a list of feature classes
        with collection(self.input_file) as src:
            return [fc['properties']['name'] for fc in src]

    def print_info(self):
        # Get the list of feature classes from the GDBHandler instance
        feature_classes = self.get_feature_classes()
        console.print(f"Feature Classes: {feature_classes}")
