#!/usr/bin/env python3
"""Basic streaming example - process chunks of text."""

# --8<-- [start:imports]
import asyncio

from hother.streamblocks import Registry, StreamBlockProcessor
from hother.streamblocks.core.types import BlockEndEvent, TextContentEvent
from hother.streamblocks_examples.blocks.agent.files import FileOperations
from hother.streamblocks_examples.helpers.simulator import simulated_stream

# --8<-- [end:imports]


# --8<-- [start:main]
async def main() -> None:
    """Process a chunked text stream."""
    # --8<-- [start:example]
    registry = Registry()
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry)

    # Text to stream in chunks
    text = "Some text before.\n!!block:files_operations\napp.py:C\n!!end\nSome text after."
    stream = simulated_stream(text, preset="fast")

    async for event in processor.process_stream(stream):
        if isinstance(event, TextContentEvent):
            print(f"[TEXT] {event.content.strip()}")
        elif isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block:
                print("\n[BLOCK] Extracted:")
                print(block.model_dump_json(indent=2))
    # --8<-- [end:example]


# --8<-- [end:main]


if __name__ == "__main__":
    asyncio.run(main())
