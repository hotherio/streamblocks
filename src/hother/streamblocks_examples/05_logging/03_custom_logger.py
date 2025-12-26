#!/usr/bin/env python3
"""Custom logger implementation example for StreamBlocks.

This example demonstrates how to implement a custom logger that works
with StreamBlocks. Any object with the required methods (debug, info,
warning, error, exception) can be used as a logger.
"""

import asyncio
from collections.abc import AsyncIterator
from textwrap import dedent
from typing import Any

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


class CustomLogger:
    """Custom logger that implements the Logger protocol.

    This shows that any object with the required methods can be used as a logger.
    Demonstrates handling direct kwargs (the StreamBlocks pattern).
    """

    def __init__(self, prefix: str = "CUSTOM") -> None:
        """Initialize custom logger with prefix."""
        self.prefix = prefix

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message with kwargs as structured data."""
        print(f"[{self.prefix} DEBUG] {msg} {kwargs}")

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log info message with kwargs as structured data."""
        print(f"[{self.prefix} INFO] {msg} {kwargs}")

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message with kwargs as structured data."""
        print(f"[{self.prefix} WARNING] {msg} {kwargs}")

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log error message with kwargs as structured data."""
        print(f"[{self.prefix} ERROR] {msg} {kwargs}")

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log exception message with kwargs as structured data."""
        print(f"[{self.prefix} EXCEPTION] {msg} {kwargs}")


async def main() -> None:
    """Use a custom logger implementation."""
    print("\n=== Custom Logger ===")

    logger = CustomLogger(prefix="MY_APP")

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
