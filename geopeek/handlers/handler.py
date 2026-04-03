from abc import ABC, abstractmethod
from typing import Dict, Any, List


class Handler(ABC):
    def __init__(self, input_file: str):
        self.input_file = input_file

    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_layers(self) -> List[str]:
        pass
