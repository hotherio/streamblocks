#!/usr/bin/env python3
"""Structlog integration example for StreamBlocks.

This example demonstrates how to use structlog for structured logging
with StreamBlocks. Structlog is an optional dependency.

Install with: uv pip install structlog
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from textwrap import dedent

from hother.streamblocks import DelimiterPreambleSyntax, Registry, StreamBlockProcessor
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
    """Use structlog for structured logging."""
    print("\n=== Structlog Integration ===")

    try:
        import structlog
    except ImportError:
        print("⚠️  structlog not installed. Install with: uv pip install structlog")
        print("   Skipping this example.")
        return

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )

    # Get a structlog logger
    logger = structlog.get_logger("streamblocks")

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
