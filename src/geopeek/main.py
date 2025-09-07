import arcpy
import typer

class GeoPeek:
    def __init__(self, gdb_path):
        """Initialize with the path to the file geodatabase."""
        self.gdb_path = gdb_path

    def list_feature_classes(self):
        """List all feature classes in the file geodatabase."""
        arcpy.env.workspace = self.gdb_path
        feature_classes = arcpy.ListFeatureClasses()
        return feature_classes

    def display_feature_classes(self):
        """Display the feature classes in the geodatabase."""
        feature_classes = self.list_feature_classes()
        print("Feature Classes in the Geodatabase:")
        for fc in feature_classes:
            print(fc)

def main(gdb_path: str):
    """Main function for geopeek."""
    geopeek = GeoPeek(gdb_path)
    geopeek.display_feature_classes()

if __name__ == "__main__":
    typer.run(main)
