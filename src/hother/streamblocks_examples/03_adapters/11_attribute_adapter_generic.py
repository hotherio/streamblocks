#!/usr/bin/env python3
"""Example 11: AttributeInputAdapter for Generic Formats.

This example shows how to use AttributeInputAdapter to handle any object
with a text-like attribute, without writing custom adapter code.
"""

import asyncio
from collections.abc import AsyncGenerator

from hother.streamblocks import (
    BlockEndEvent,
    DelimiterPreambleSyntax,
    Registry,
    StreamBlockProcessor,
)
from hother.streamblocks.adapters.input import AttributeInputAdapter
from hother.streamblocks_examples.blocks.agent.files import FileOperations


# Generic chunk classes
class ResponseChunk:
    """Some API response with 'message' attribute."""

    def __init__(self, message: str, status: str = "active") -> None:
        self.message = message  # Text is in 'message'
        self.status = status
        self.finish_reason: str | None = None


class FinalChunk(ResponseChunk):
    """Final chunk with finish_reason."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status="complete")
        self.finish_reason: str | None = "done"


async def generic_stream() -> AsyncGenerator[ResponseChunk]:
    """Stream with generic chunk objects."""
    chunks = [
        ResponseChunk("!!files:files_operations\n"),
        ResponseChunk("src/app.py:C\n"),
        ResponseChunk("src/utils.py:C\n"),
        ResponseChunk("!!end\n"),
        FinalChunk(""),  # Final chunk
    ]

    for chunk in chunks:
        yield chunk
        await asyncio.sleep(0.1)


async def main() -> None:
    """Run the example."""
    print("=" * 60)
    print("Example 11: AttributeInputAdapter (Generic Objects)")
    print("=" * 60)
    print()

    # Create adapter for 'message' attribute
    adapter = AttributeInputAdapter(text_attr="message")

    # Setup
    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry)

    print("Processing stream with AttributeInputAdapter (text_attr='message')...")
    print()

    async for event in processor.process_stream(generic_stream(), adapter=adapter):
        # Original chunks
        if isinstance(event, (ResponseChunk, FinalChunk)):
            print(f"Chunk: message={repr(event.message)[:30]}, status={event.status}")
            if event.finish_reason:
                print(f"   Finish reason: {event.finish_reason}")

        # Blocks
        elif isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is None:
                continue
            print("\nBlock Extracted:")
            print(block.model_dump_json(indent=2))
            print()

    print()
    print("Works with any object")
    print("Just specify attribute name")
    print("Handles finish_reason automatically")
    print()
    print("Other common attributes:")
    print("  - text_attr='text' (default)")
    print("  - text_attr='content'")
    print("  - text_attr='data'")
    print("  - text_attr='message'")


if __name__ == "__main__":
    asyncio.run(main())
