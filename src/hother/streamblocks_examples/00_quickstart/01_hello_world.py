#!/usr/bin/env python3
"""Simplest StreamBlocks example - extract a block from text."""

# --8<-- [start:imports]
import asyncio

from hother.streamblocks import Registry, StreamBlockProcessor
from hother.streamblocks.core.types import BlockEndEvent
from hother.streamblocks_examples.blocks.agent.files import FileOperations
from hother.streamblocks_examples.helpers.simulator import simple_text_stream

# --8<-- [end:imports]


# --8<-- [start:main]
async def main() -> None:
    """Extract a single block from a text stream."""
    # --8<-- [start:example]
    # Setup: registry + processor
    registry = Registry()
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry)

    # Text with one block
    text = "!!block01:files_operations\nsrc/main.py:C\n!!end"
    stream = simple_text_stream(text)

    # Process and extract blocks
    async for event in processor.process_stream(stream):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block:
                print("Extracted block:")
                print(block.model_dump_json(indent=2))
    # --8<-- [end:example]


# --8<-- [end:main]


if __name__ == "__main__":
    asyncio.run(main())
