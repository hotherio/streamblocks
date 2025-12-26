#!/usr/bin/env python3
"""Example 09: Custom Adapter with Registration.

This example shows how to create a custom input adapter for a proprietary
streaming format and register it for auto-detection.
"""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from hother.streamblocks import (
    BlockEndEvent,
    DelimiterPreambleSyntax,
    EventCategory,
    InputAdapterRegistry,
    Registry,
    StreamBlockProcessor,
)
from hother.streamblocks_examples.blocks.agent.files import FileOperations


# Custom streaming format
class ProprietaryChunk:
    """Custom chunk format from proprietary API."""

    __module__ = "mycompany.streaming.api"

    def __init__(self, payload: str, meta: dict[str, str | bool] | None = None) -> None:
        self.payload = payload  # Text is in 'payload'
        self.meta = meta or {}  # Metadata in 'meta'


# Custom adapter implementing the InputProtocolAdapter protocol
class ProprietaryInputAdapter:
    """Input adapter for proprietary streaming format."""

    def categorize(self, event: ProprietaryChunk) -> EventCategory:
        """All events contain text content."""
        return EventCategory.TEXT_CONTENT

    def extract_text(self, chunk: ProprietaryChunk) -> str | None:
        """Extract text from payload field."""
        return chunk.payload

    def is_complete(self, chunk: ProprietaryChunk) -> bool:
        """Check if stream is complete."""
        return chunk.meta.get("final", False)

    def get_metadata(self, chunk: ProprietaryChunk) -> dict[str, Any] | None:
        """Extract metadata."""
        if chunk.meta:
            return {
                "request_id": chunk.meta.get("request_id"),
                "timestamp": chunk.meta.get("timestamp"),
            }
        return None


async def proprietary_stream() -> AsyncGenerator[ProprietaryChunk]:
    """Simulate proprietary API stream."""
    chunks = [
        ProprietaryChunk("!!proj:files_operations\n", {"request_id": "req-123"}),
        ProprietaryChunk("main.py:C\n", {"timestamp": "2024-01-01"}),
        ProprietaryChunk("test.py:C\n", {"timestamp": "2024-01-01"}),
        ProprietaryChunk("!!end\n", {"final": True}),
    ]

    for chunk in chunks:
        yield chunk
        await asyncio.sleep(0.1)


async def main() -> None:
    """Run the example."""
    print("=" * 60)
    print("Example 09: Custom Adapter with Registration")
    print("=" * 60)
    print()

    # Register custom adapter for auto-detection
    print("Registering custom adapter...")
    InputAdapterRegistry.register_module(
        "mycompany.streaming",
        ProprietaryInputAdapter,
    )
    print("Registered for module: mycompany.streaming.*")
    print()

    # Setup
    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry)

    print("Processing proprietary stream (auto-detecting custom adapter)...")
    print()

    async for event in processor.process_stream(proprietary_stream()):
        # Original chunks
        if isinstance(event, ProprietaryChunk):
            print("Proprietary Chunk:")
            print(f"   Payload: {repr(event.payload)[:40]}")
            print(f"   Meta: {event.meta}")

        # Extracted blocks
        elif isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is None:
                continue
            print("\nBlock Extracted:")
            print(block.model_dump_json(indent=2))
            print()

    # Cleanup - remove from registry
    del InputAdapterRegistry._type_registry["mycompany.streaming"]

    print()
    print("Custom adapter created")
    print("Registered for auto-detection")
    print("Works with proprietary formats")


if __name__ == "__main__":
    asyncio.run(main())
