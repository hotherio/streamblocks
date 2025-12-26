#!/usr/bin/env python3
"""Custom output adapter for simplified JSON event format."""

# --8<-- [start:imports]
import asyncio
from textwrap import dedent
from typing import Any

from hother.streamblocks import DelimiterFrontmatterSyntax, Registry
from hother.streamblocks.core.protocol_processor import ProtocolStreamProcessor
from hother.streamblocks.core.types import (
    BaseEvent,
    BlockEndEvent,
    BlockStartEvent,
    TextContentEvent,
)
from hother.streamblocks_examples.blocks.agent.files import FileOperations

# --8<-- [end:imports]


# --8<-- [start:output_adapter]
class JsonEventAdapter:
    """Output adapter that emits simplified JSON-like dicts.

    Features:
    - Return None to filter out events
    - Return a list to emit multiple events
    - Transform events to any output format
    """

    def to_protocol_event(self, event: BaseEvent) -> dict[str, Any] | list[dict[str, Any]] | None:
        """Convert StreamBlocks events to simplified dicts."""
        # Filter out text content events (we only care about blocks)
        if isinstance(event, TextContentEvent):
            return None

        # Emit block start and end as separate events
        if isinstance(event, BlockStartEvent):
            return {"event": "block_start", "block_id": event.block_id}

        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block:
                # Emit multiple events: block info + operations
                events: list[dict[str, Any]] = [
                    {
                        "event": "block_end",
                        "block_id": block.metadata.id,
                        "block_type": block.metadata.block_type,
                    },
                ]
                # Add operation details
                if hasattr(block.content, "operations"):
                    for op in block.content.operations:
                        events.append(
                            {
                                "event": "operation",
                                "action": op.action,
                                "path": op.path,
                            }
                        )
                return events

        return None

    def passthrough(self, original_event: Any) -> dict[str, Any] | None:
        """Handle passthrough events."""
        return {"event": "passthrough", "data": str(original_event)}


# --8<-- [end:output_adapter]


# --8<-- [start:main]
async def main() -> None:
    """Demonstrate custom output adapter."""
    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)

    # --8<-- [start:setup]
    processor = ProtocolStreamProcessor[str, dict[str, Any]](
        registry,
        output_adapter=JsonEventAdapter(),
    )
    # --8<-- [end:setup]

    # --8<-- [start:stream]
    text = dedent("""
        !!start
        ---
        id: ops001
        block_type: files_operations
        ---
        src/main.py:C
        src/utils.py:E
        !!end
    """).strip()

    from hother.streamblocks_examples.helpers.simulator import simple_text_stream

    print("=== Custom Output Adapter ===")
    async for event in processor.process_stream(simple_text_stream(text)):
        print(event)
    # --8<-- [end:stream]


# --8<-- [end:main]


if __name__ == "__main__":
    asyncio.run(main())
