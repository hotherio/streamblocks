"""Base content models for StreamBlocks."""

from pydantic import BaseModel


class BaseContent(BaseModel):
    """Base class for content models with common parsing interface."""

    @classmethod
    def parse(cls, text: str) -> "BaseContent":
        """Parse text into content model.

        Args:
            text: Raw text to parse

        Returns:
            Parsed content model instance

        Raises:
            ValueError: If text cannot be parsed
        """
        raise NotImplementedError("Subclasses must implement parse method")
