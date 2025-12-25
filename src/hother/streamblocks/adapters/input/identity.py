"""Built-in input adapters with no external dependencies."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from hother.streamblocks.adapters.categories import EventCategory


@runtime_checkable
class HasFinishReason(Protocol):
    """Protocol for events with a finish_reason attribute."""

    finish_reason: str | None


@runtime_checkable
class HasModel(Protocol):
    """Protocol for events with a model attribute."""

    model: str


class IdentityInputAdapter:
    """Input adapter for plain text streams.

    This adapter treats all input as text content and passes it through unchanged.
    It's the simplest adapter for processing raw text streams.

    Example:
        >>> adapter = IdentityInputAdapter()
        >>> adapter.categorize("Hello world")
        EventCategory.TEXT_CONTENT
        >>> adapter.extract_text("Hello world")
        'Hello world'
    """

    def categorize(self, event: str) -> EventCategory:
        """Categorize event - all strings are text content.

        Args:
            event: Input string

        Returns:
            Always TEXT_CONTENT for string inputs
        """
        return EventCategory.TEXT_CONTENT

    def extract_text(self, event: str) -> str | None:
        """Extract text - return the string unchanged.

        Args:
            event: Input string

        Returns:
            The input string
        """
        return event

    def get_metadata(self, event: str) -> dict[str, Any] | None:
        """No metadata for plain text.

        Args:
            event: Input string

        Returns:
            None - plain text has no metadata
        """
        return None

    def is_complete(self, event: str) -> bool:
        """Plain text streams don't have explicit completion markers.

        Args:
            event: Input string

        Returns:
            Always False for plain text
        """
        return False


class AttributeInputAdapter:
    """Generic input adapter for objects with a text attribute.

    Works for any object that has a specified attribute (e.g., chunk.text or chunk.content).
    Automatically detects completion via finish_reason attribute if present.

    Example:
        >>> # For chunks with .text attribute
        >>> adapter = AttributeInputAdapter("text")
        >>> adapter.extract_text(chunk)
        'Hello world'
        >>>
        >>> # For chunks with .content attribute
        >>> adapter = AttributeInputAdapter("content")
        >>> adapter.extract_text(chunk)
        'Hello world'
    """

    def __init__(self, text_attr: str = "text") -> None:
        """Initialize attribute adapter.

        Args:
            text_attr: Name of the attribute containing text (default: "text")
        """
        self.text_attr = text_attr

    def categorize(self, event: Any) -> EventCategory:
        """Categorize event - all events are text content.

        Args:
            event: Input event

        Returns:
            Always TEXT_CONTENT
        """
        return EventCategory.TEXT_CONTENT

    def extract_text(self, event: Any) -> str | None:
        """Extract text from specified attribute.

        Args:
            event: Input event with text attribute

        Returns:
            Text from the specified attribute, or None if not present
        """
        return getattr(event, self.text_attr, None)

    def get_metadata(self, event: Any) -> dict[str, Any] | None:
        """Extract common metadata fields if present.

        Args:
            event: Input event

        Returns:
            Dictionary with finish_reason and model if present, or None
        """
        metadata: dict[str, Any] = {}

        # Extract finish reason using Protocol
        if isinstance(event, HasFinishReason) and event.finish_reason:
            metadata["finish_reason"] = event.finish_reason

        # Extract model using Protocol
        if isinstance(event, HasModel):
            metadata["model"] = event.model

        return metadata if metadata else None

    def is_complete(self, event: Any) -> bool:
        """Check for finish_reason or similar completion marker.

        Args:
            event: Input event

        Returns:
            True if event has a finish_reason attribute with a truthy value
        """
        if isinstance(event, HasFinishReason):
            return event.finish_reason is not None
        return False
