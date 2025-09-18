"""Base content models."""

from pydantic import BaseModel, Field


class BaseContent(BaseModel):
    """Base class for content models."""

    raw: str = Field(default="", description="Raw text content")
    text: str = Field(default="", description="Text content (alias for raw)")

    def __init__(self, **data: object) -> None:
        """Initialize content, handling both 'raw' and 'text' fields."""
        # If 'text' is provided but not 'raw', copy it
        if "text" in data and "raw" not in data:
            data["raw"] = data["text"]
        # If 'raw' is provided but not 'text', copy it
        elif "raw" in data and "text" not in data:
            data["text"] = data["raw"]
        super().__init__(**data)
