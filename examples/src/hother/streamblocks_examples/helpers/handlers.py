"""Event handlers for examples."""

from typing import TYPE_CHECKING, Any

from hother.streamblocks.core.types import (
    BlockContentDeltaEvent,
    BlockEndEvent,
    BlockErrorEvent,
    BlockHeaderDeltaEvent,
    BlockMetadataDeltaEvent,
    TextContentEvent,
)

if TYPE_CHECKING:
    from hother.streamblocks.core.models import ExtractedBlock
    from hother.streamblocks.core.types import BaseContent, BaseMetadata


def print_events(event: Any, *, show_deltas: bool = False) -> None:
    """Print event information to console.

    Args:
        event: StreamBlocks event to print.
        show_deltas: Whether to print delta events.
    """
    if isinstance(event, TextContentEvent):
        text = event.content.strip()
        if text:
            print(f"[TEXT] {text}")

    elif isinstance(event, BlockEndEvent):
        block = event.get_block()
        if block:
            print(f"[BLOCK] {block.metadata.id} ({block.metadata.block_type})")

    elif isinstance(event, BlockErrorEvent):
        print(f"[ERROR] {event.reason}")

    elif show_deltas and isinstance(event, (BlockHeaderDeltaEvent, BlockMetadataDeltaEvent, BlockContentDeltaEvent)):
        section = event.type.value.replace("BLOCK_", "").replace("_DELTA", "").lower()
        print(f"[DELTA] {section}: {event.delta.strip()}")


async def collect_blocks(
    events: Any,
) -> list["ExtractedBlock[BaseMetadata, BaseContent]"]:
    """Collect all blocks from an event stream.

    Args:
        events: Async iterator of StreamBlocks events.

    Returns:
        List of extracted blocks.
    """
    blocks: list[ExtractedBlock[BaseMetadata, BaseContent]] = []
    async for event in events:
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block:
                blocks.append(block)
    return blocks
