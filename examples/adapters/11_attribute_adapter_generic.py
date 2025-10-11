#!/usr/bin/env python3
"""Example 11: AttributeAdapter for Generic Formats.

This example shows how to use AttributeAdapter to handle any object
with a text-like attribute, without writing custom adapter code.
"""

import asyncio

from hother.streamblocks import (
    AttributeAdapter,
    BlockExtractedEvent,
    DelimiterPreambleSyntax,
    Registry,
    StreamBlockProcessor,
)
from hother.streamblocks.blocks import FileOperations


# Generic chunk classes
class ResponseChunk:
    """Some API response with 'message' attribute."""

    def __init__(self, message, status="active") -> None:
        self.message = message  # Text is in 'message'
        self.status = status
        self.finish_reason = None


class FinalChunk(ResponseChunk):
    """Final chunk with finish_reason."""

    def __init__(self, message) -> None:
        super().__init__(message, status="complete")
        self.finish_reason = "done"


async def generic_stream():
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
    print("Example 11: AttributeAdapter (Generic Objects)")
    print("=" * 60)
    print()

    # Create adapter for 'message' attribute
    adapter = AttributeAdapter(text_attr="message")

    # Setup
    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry)

    print("Processing stream with AttributeAdapter (text_attr='message')...")
    print()

    async for event in processor.process_stream(generic_stream(), adapter=adapter):
        # Original chunks
        if isinstance(event, (ResponseChunk, FinalChunk)):
            print(f"📦 Chunk: message={repr(event.message)[:30]}, status={event.status}")
            if event.finish_reason:
                print(f"   🏁 Finish reason: {event.finish_reason}")

        # Blocks
        elif isinstance(event, BlockExtractedEvent):
            print(f"\n✅ Block: {event.block.metadata.id}")
            for op in event.block.content.operations:
                print(f"   - {op.path}")
            print()

    print()
    print("✓ Works with any object")
    print("✓ Just specify attribute name")
    print("✓ Handles finish_reason automatically")
    print()
    print("Other common attributes:")
    print("  - text_attr='text' (default)")
    print("  - text_attr='content'")
    print("  - text_attr='data'")
    print("  - text_attr='message'")


if __name__ == "__main__":
    asyncio.run(main())
