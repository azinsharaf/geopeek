class GeoPeek:
    def __init__(self, gdb_path: str):
        self.gdb_path = gdb_path

    def list_feature_classes(self):
        # Implement actual logic to list feature classes in the geodatabase
        try:
            # Example logic (replace with actual implementation)
            return ["FeatureClass1", "FeatureClass2", "FeatureClass3"]
        except Exception as e:
            print(f"Error listing feature classes: {e}")
            return []
