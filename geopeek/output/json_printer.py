import json

def print_json(metadata: dict):
    """Print metadata as JSON."""
    print(json.dumps(metadata, indent=2))
