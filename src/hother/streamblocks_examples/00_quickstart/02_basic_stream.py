#!/usr/bin/env python3
"""Basic streaming example - process chunks of text."""

# --8<-- [start:imports]
import asyncio

from hother.streamblocks import DelimiterPreambleSyntax, Registry, StreamBlockProcessor
from hother.streamblocks.core.types import BlockEndEvent, TextContentEvent
from hother.streamblocks_examples.blocks.agent.files import FileOperations
from hother.streamblocks_examples.helpers.simulator import simulated_stream

# --8<-- [end:imports]


# --8<-- [start:main]
async def main() -> None:
    """Process a chunked text stream."""
    # --8<-- [start:example]
    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry)

    # Text to stream in chunks
    text = "Some text before.\n!!block:files_operations\napp.py:C\n!!end\nSome text after."

    async for event in processor.process_stream(simulated_stream(text, preset="fast")):
        if isinstance(event, TextContentEvent):
            print(f"[TEXT] {event.content.strip()}")
        elif isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block:
                print(f"[BLOCK] {block.metadata.id}")
    # --8<-- [end:example]


# --8<-- [end:main]


if __name__ == "__main__":
    asyncio.run(main())
