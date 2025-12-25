#!/usr/bin/env python3
"""Simplest StreamBlocks example - extract a block from text."""

# --8<-- [start:imports]
import asyncio

from examples.blocks.agent.files import FileOperations
from hother.streamblocks import DelimiterPreambleSyntax, Registry, StreamBlockProcessor
from hother.streamblocks.core.types import BlockEndEvent

# --8<-- [end:imports]


# --8<-- [start:main]
async def main() -> None:
    """Extract a single block from a text stream."""
    # --8<-- [start:example]
    # Setup: syntax + registry + processor
    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry)

    # Simple stream yielding text with one block
    async def stream():
        yield "!!block01:files_operations\nsrc/main.py:C\n!!end"

    # Process and extract blocks
    async for event in processor.process_stream(stream()):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block:
                print(f"Extracted block: {block.metadata.id}")
    # --8<-- [end:example]


# --8<-- [end:main]


if __name__ == "__main__":
    asyncio.run(main())
