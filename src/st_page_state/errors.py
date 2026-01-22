from typing import Any

class StPageStateError(Exception):
    """Base exception for st-page-state."""

    pass

class InvalidQueryParamError(StPageStateError):
    """Raised when a query param cannot be converted to the target type."""

    def __init__(self, key: str, value: str, target_type: Any, original_error: Exception):
        super().__init__(f"Failed to parse query param '{key}={value}' as {target_type}: {original_error}")