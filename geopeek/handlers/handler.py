from abc import ABC, abstractmethod

class Handler(ABC):
    def __init__(self, input_file):
        self.input_file = input_file

    @abstractmethod
    def get_info(self):
        pass
