"""Logging integration examples for StreamBlocks.

This example demonstrates how to use different logging libraries with StreamBlocks.
StreamBlocks accepts any logger that implements the standard Python logging interface
(debug, info, warning, error, exception methods).
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from hother.streamblocks import DelimiterPreambleSyntax, EventType, Registry, StreamBlockProcessor
from hother.streamblocks.blocks.files import FileOperations
from hother.streamblocks.core._logger import StdlibLoggerAdapter


async def example_stream() -> AsyncIterator[str]:
    """Example stream with file operations blocks."""
    text = """
!!file01:files_operations
src/main.py:C
src/utils.py:E
!!end

!!file02:files_operations
tests/test_main.py:C
!!end
"""
    chunk_size = 30
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        yield chunk
        await asyncio.sleep(0.01)


# Example 1: Stdlib logging with adapter
async def example_stdlib_logging() -> None:
    """Use stdlib logging with StdlibLoggerAdapter.

    The adapter automatically displays structured data - just wrap your logger!
    """
    print("\n=== Example 1: Stdlib logging with adapter ===")

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

    processor = StreamBlockProcessor(registry, logger=logger, lines_buffer=5)

    async for event in processor.process_stream(example_stream()):
        if event.type == EventType.BLOCK_EXTRACTED:
            print(f"✓ Extracted block: {event.block.metadata.id}")


# Example 2: Structlog integration (optional dependency)
async def example_structlog() -> None:
    """Use structlog for structured logging."""
    print("\n=== Example 2: Structlog integration ===")

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

    processor = StreamBlockProcessor(registry, logger=logger, lines_buffer=5)

    async for event in processor.process_stream(example_stream()):
        if event.type == EventType.BLOCK_EXTRACTED:
            print(f"✓ Extracted block: {event.block.metadata.id}")


# Example 3: Custom logger implementation
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


async def example_custom_logger() -> None:
    """Use a custom logger implementation."""
    print("\n=== Example 3: Custom logger ===")

    logger = CustomLogger(prefix="MY_APP")

    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax, logger=logger)
    registry.register("files_operations", FileOperations)

    processor = StreamBlockProcessor(registry, logger=logger, lines_buffer=5)

    async for event in processor.process_stream(example_stream()):
        if event.type == EventType.BLOCK_EXTRACTED:
            print(f"✓ Extracted block: {event.block.metadata.id}")


# Example 4: Disable logging
class NoOpLogger:
    """No-op logger that discards all log messages."""

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Do nothing."""

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Do nothing."""

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Do nothing."""

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Do nothing."""

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Do nothing."""


async def example_disabled_logging() -> None:
    """Disable logging completely."""
    print("\n=== Example 4: Disabled logging ===")

    logger = NoOpLogger()

    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax, logger=logger)
    registry.register("files_operations", FileOperations)

    processor = StreamBlockProcessor(registry, logger=logger, lines_buffer=5)

    async for event in processor.process_stream(example_stream()):
        if event.type == EventType.BLOCK_EXTRACTED:
            print(f"✓ Extracted block: {event.block.metadata.id}")


async def main() -> None:
    """Run all logging examples."""
    print("StreamBlocks Logging Integration Examples")
    print("=" * 60)

    await example_stdlib_logging()
    await example_structlog()
    await example_custom_logger()
    await example_disabled_logging()

    print("\n" + "=" * 60)
    print("All examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(main())
