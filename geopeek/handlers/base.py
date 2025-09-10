class BaseHandler:
    @staticmethod
    def can_open(path: str) -> bool:
        raise NotImplementedError("Subclasses must implement this method")

    @staticmethod
    def info(path: str) -> dict:
        raise NotImplementedError("Subclasses must implement this method")
