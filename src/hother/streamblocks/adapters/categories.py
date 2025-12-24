"""Event categories for protocol adapter routing."""

from __future__ import annotations

from enum import StrEnum


class EventCategory(StrEnum):
    """Semantic categorization of protocol events.

    These three categories are EXHAUSTIVE - every protocol event falls into one:

    - TEXT_CONTENT: Event contains text that should be processed by StreamBlocks
    - PASSTHROUGH: Event should pass through unchanged to output
    - SKIP: Event should not be emitted in output at all
    """

    TEXT_CONTENT = "text_content"
    """Event contains text content that should be processed by StreamBlocks."""

    PASSTHROUGH = "passthrough"
    """Event has no text content and should pass through unchanged to output."""

    SKIP = "skip"
    """Event should not be included in output at all."""
