"""Message content models for AI-to-user communication blocks."""

from __future__ import annotations

from typing import Literal

from hother.streamblocks.core.models import Block
from hother.streamblocks.core.types import BaseContent, BaseMetadata


class MessageMetadata(BaseMetadata):
    """Metadata for message/communication blocks."""

    block_type: Literal["message"] = "message"

    # message_type determines how the message is displayed
    message_type: Literal["info", "warning", "error", "success", "status", "explanation"]

    # Optional title for the message
    title: str | None = None

    # Priority level for the message
    priority: Literal["low", "normal", "high"] = "normal"


class MessageContent(BaseContent):
    """Content model for message blocks."""

    # The raw_content field from BaseContent contains the message text

    @classmethod
    def parse(cls, raw_text: str) -> MessageContent:
        """Parse message content - just stores the raw text."""
        return cls(raw_content=raw_text.strip())


# Block configuration class


class Message(Block[MessageMetadata, MessageContent]):
    """Message block configuration."""
