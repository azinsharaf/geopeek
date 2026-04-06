from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class Handler(ABC):
    def __init__(self, input_file: str):
        self.input_file = input_file

    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_layers(self) -> List[str]:
        pass

    @abstractmethod
    def get_schema(self, layer_name: Optional[str] = None) -> Dict[str, Any]:
        """Return field/band schema for the dataset or a specific layer."""
        pass

    @abstractmethod
    def get_extent(self, layer_name: Optional[str] = None) -> Dict[str, Any]:
        """Return bounding box extent for the dataset or a specific layer."""
        pass

    @abstractmethod
    def peek(self, limit: int = 10, layer_name: Optional[str] = None) -> Dict[str, Any]:
        """Return a preview of the data (attribute rows or band stats)."""
        pass
