#!/usr/bin/env python3
"""Example 05: Mixed Event Streams.

This example demonstrates how to handle a stream containing BOTH
original chunks and StreamBlocks events. Shows type checking patterns.
"""

import asyncio

from hother.streamblocks import (
    BlockExtractedEvent,
    BlockOpenedEvent,
    DelimiterPreambleSyntax,
    RawTextEvent,
    Registry,
    StreamBlockProcessor,
    TextDeltaEvent,
)
from hother.streamblocks.blocks import FileOperations


# Custom chunk type
class MyCustomChunk:
    """Custom chunk with metadata."""

    def __init__(self, text, metadata=None) -> None:
        self.text = text
        self.metadata = metadata or {}


async def custom_stream():
    """Stream with custom chunks."""
    chunks = [
        MyCustomChunk("!!files:files_operations\n", {"source": "api"}),
        MyCustomChunk("main.py:C\n", {"line": 1}),
        MyCustomChunk("test.py:C\n", {"line": 2}),
        MyCustomChunk("!!end\n", {"source": "api"}),
    ]

    for chunk in chunks:
        yield chunk
        await asyncio.sleep(0.05)


async def main() -> None:
    """Run the example."""
    print("=" * 60)
    print("Example 05: Mixed Event Streams")
    print("=" * 60)
    print()

    # Setup
    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry)

    print("Processing stream - showing both original and StreamBlocks events:")
    print()

    # Counters
    original_count = 0
    streamblocks_count = 0

    async for event in processor.process_stream(custom_stream()):
        # Check if it's an original chunk
        if isinstance(event, MyCustomChunk):
            original_count += 1
            print(f"📦 Original Chunk #{original_count}:")
            print(f"   Text: {event.text!r}")
            print(f"   Metadata: {event.metadata}")

        # Check if it's a StreamBlocks event
        elif isinstance(event, TextDeltaEvent):
            streamblocks_count += 1
            print(f"🔵 TextDelta: {repr(event.delta)[:40]}")

        elif isinstance(event, BlockOpenedEvent):
            streamblocks_count += 1
            print(f"🟢 BlockOpened: {event.syntax}")

        elif isinstance(event, BlockExtractedEvent):
            streamblocks_count += 1
            print(f"✅ BlockExtracted: {event.block.metadata.id}")
            for op in event.block.content.operations:
                print(f"   - {op.path}")

        elif isinstance(event, RawTextEvent):
            streamblocks_count += 1
            print(f"💬 RawText: {event.data}")

    print()
    print("Summary:")
    print(f"  Original chunks: {original_count}")
    print(f"  StreamBlocks events: {streamblocks_count}")
    print()
    print("✓ Both event types in same stream")
    print("✓ Type checking with isinstance()")
    print("✓ Original metadata preserved")


if __name__ == "__main__":
    asyncio.run(main())
