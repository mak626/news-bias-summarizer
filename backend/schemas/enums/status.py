from enum import Enum


class ResponseStatus(str, Enum):
    """API response status."""
    SUCCESS = "success"
    ERROR = "error"
