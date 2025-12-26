#!/usr/bin/env python3
"""Stdlib logging integration example for StreamBlocks.

This example demonstrates how to use Python's standard library logging
with StreamBlocks using the StdlibLoggerAdapter for structured logging.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from textwrap import dedent

from hother.streamblocks import DelimiterPreambleSyntax, Registry, StreamBlockProcessor
from hother.streamblocks.core._logger import StdlibLoggerAdapter
from hother.streamblocks.core.types import BlockEndEvent
from hother.streamblocks_examples.blocks.agent.files import FileOperations


async def example_stream() -> AsyncIterator[str]:
    """Example stream with file operations blocks."""
    text = dedent("""
        !!file01:files_operations
        src/main.py:C
        src/utils.py:E
        !!end

        !!file02:files_operations
        tests/test_main.py:C
        !!end
    """)
    chunk_size = 30
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        yield chunk
        await asyncio.sleep(0.01)


async def main() -> None:
    """Use stdlib logging with StdlibLoggerAdapter.

    The adapter automatically displays structured data - just wrap your logger!
    """
    print("\n=== Stdlib Logging with Adapter ===")

    # Configure stdlib logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

    # Wrap stdlib logger with adapter to enable direct kwargs and auto-display
    stdlib_logger = logging.getLogger("my_app.streamblocks")
    logger = StdlibLoggerAdapter(stdlib_logger)

    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax, logger=logger)
    registry.register("files_operations", FileOperations)

    from hother.streamblocks.core.processor import ProcessorConfig

    config = ProcessorConfig(lines_buffer=5)
    processor = StreamBlockProcessor(registry, config=config, logger=logger)

    async for event in processor.process_stream(example_stream()):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is not None:
                print("✓ Extracted block:")
                print(block.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
