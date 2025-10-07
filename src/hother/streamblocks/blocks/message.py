"""Message content models for AI-to-user communication blocks."""

from __future__ import annotations

from typing import Literal

from hother.streamblocks.core.models import BaseContent, BaseMetadata, BlockDefinition


class MessageMetadata(BaseMetadata):
    """Metadata for message/communication blocks."""

    # message_type determines how the message is displayed
    message_type: Literal["info", "warning", "error", "success", "status", "explanation"]

    # Optional title for the message
    title: str | None = None

    # Priority level for the message
    priority: Literal["low", "normal", "high"] = "normal"

    def __init__(self, **data: object) -> None:
        # Set default block_type if not provided
        if "block_type" not in data:
            data["block_type"] = "message"
        super().__init__(**data)


class MessageContent(BaseContent):
    """Content model for message blocks."""

    # The raw_content field from BaseContent contains the message text

    @classmethod
    def parse(cls, raw_text: str) -> MessageContent:
        """Parse message content - just stores the raw text."""
        return cls(raw_content=raw_text.strip())


# Block class (aggregated metadata + content)


class Message(BlockDefinition):
    """Message block."""

    # Link to metadata/content classes for syntax parsing
    __metadata_class__ = MessageMetadata
    __content_class__ = MessageContent

    # From metadata:
    id: str
    block_type: Literal["message"] = "message"
    message_type: Literal["info", "warning", "error", "success", "status", "explanation"]
    title: str | None = None
    priority: Literal["low", "normal", "high"] = "normal"

    # From content:
    raw_content: str
