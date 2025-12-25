"""Event filter for AG-UI output adapter."""

from __future__ import annotations

from enum import Flag, auto


class AGUIEventFilter(Flag):
    """Configurable event filtering for AG-UI output adapter.

    Use these flags to control which StreamBlocks events are emitted
    when using AGUIOutputAdapter.

    Example:
        >>> # Only emit block-related events
        >>> filter = AGUIEventFilter.BLOCKS_ONLY
        >>>
        >>> # Emit blocks with progress updates
        >>> filter = AGUIEventFilter.BLOCKS_WITH_PROGRESS
        >>>
        >>> # Custom combination
        >>> filter = AGUIEventFilter.TEXT_DELTA | AGUIEventFilter.BLOCK_EXTRACTED
    """

    NONE = 0
    """Emit no StreamBlocks events."""

    RAW_TEXT = auto()
    """Emit RawTextEvent as TextMessageContentEvent."""

    TEXT_DELTA = auto()
    """Emit TextDeltaEvent as TextMessageContentEvent."""

    BLOCK_OPENED = auto()
    """Emit BlockOpenedEvent as CustomEvent."""

    BLOCK_DELTA = auto()
    """Emit section delta events (BlockHeaderDeltaEvent, BlockMetadataDeltaEvent, BlockContentDeltaEvent) as CustomEvent."""

    BLOCK_EXTRACTED = auto()
    """Emit BlockExtractedEvent as CustomEvent."""

    BLOCK_REJECTED = auto()
    """Emit BlockRejectedEvent as CustomEvent."""

    # Presets
    ALL = RAW_TEXT | TEXT_DELTA | BLOCK_OPENED | BLOCK_DELTA | BLOCK_EXTRACTED | BLOCK_REJECTED
    """Emit all StreamBlocks events."""

    BLOCKS_ONLY = BLOCK_OPENED | BLOCK_EXTRACTED | BLOCK_REJECTED
    """Emit only block lifecycle events (opened, extracted, rejected)."""

    BLOCKS_WITH_PROGRESS = BLOCK_OPENED | BLOCK_DELTA | BLOCK_EXTRACTED | BLOCK_REJECTED
    """Emit block lifecycle events plus progress updates."""

    TEXT_AND_FINAL = TEXT_DELTA | BLOCK_EXTRACTED | BLOCK_REJECTED
    """Emit text streaming plus final block results."""
