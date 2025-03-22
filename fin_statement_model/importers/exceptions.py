class MappingError(Exception):
    """Exception raised for errors in the metric mapping process."""

    def __init__(self, message: str = None):
        super().__init__(message)

    def __str__(self):
        return f"MappingError: {self.args[0] if self.args else 'An error occurred in metric mapping.'}" 