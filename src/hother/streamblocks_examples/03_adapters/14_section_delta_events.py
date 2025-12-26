"""Example demonstrating section-specific delta events.

This example shows how to use BlockHeaderDeltaEvent, BlockMetadataDeltaEvent,
and BlockContentDeltaEvent for type-safe handling of different block sections.

Section-specific events provide:
- Type safety: isinstance() checks work without runtime string comparisons
- Unique fields: Each event type can have section-specific fields
- Clear intent: Code clearly expresses which section is being handled
"""

import asyncio
from collections.abc import AsyncIterator

from hother.streamblocks import (
    DelimiterFrontmatterSyntax,
    Registry,
    StreamBlockProcessor,
)
from hother.streamblocks.core.processor import ProcessorConfig
from hother.streamblocks.core.types import (
    BlockContentDeltaEvent,
    BlockEndEvent,
    BlockHeaderDeltaEvent,
    BlockMetadataDeltaEvent,
    BlockStartEvent,
    TextContentEvent,
)


async def example_stream() -> AsyncIterator[str]:
    """Example stream with a delimiter frontmatter block."""
    text = """Here's some introductory text before the block.

!!start
---
id: config-update
block_type: config
version: 2.0
author: dev-team
---
database:
  host: localhost
  port: 5432
  driver: postgresql

logging:
  level: INFO
  format: json
!!end

And some text after the block.
"""

    # Simulate streaming by yielding chunks
    chunk_size = 40
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        yield chunk
        await asyncio.sleep(0.02)


async def main() -> None:
    """Demonstrate section-specific delta events."""
    # Create syntax and registry
    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)

    # Create processor with text deltas disabled for clarity
    config = ProcessorConfig(emit_text_deltas=False)  # Disable TextDeltaEvent for cleaner output
    processor = StreamBlockProcessor(registry, config=config)

    print("=" * 70)
    print("SECTION-SPECIFIC DELTA EVENTS DEMONSTRATION")
    print("=" * 70)
    print()
    print("Processing stream and capturing section-specific events...")
    print()

    # Counters for different event types
    header_count = 0
    metadata_count = 0
    content_count = 0

    # Store accumulated content by section
    metadata_lines: list[str] = []
    content_lines: list[str] = []

    async for event in processor.process_stream(example_stream()):
        # Handle lifecycle events
        if isinstance(event, BlockStartEvent):
            print(f"[START] Block opened at line {event.start_line}")
            print(f"        Syntax: {event.syntax}")
            print(f"        Block ID: {event.block_id}")
            print()

        # Handle section-specific delta events with type safety
        elif isinstance(event, BlockHeaderDeltaEvent):
            # Type-safe: isinstance check works!
            header_count += 1
            print(f"[HEADER] Line {event.current_line}: {event.delta!r}")

            # Header-specific field: inline_metadata
            if event.inline_metadata:
                print(f"         Inline metadata: {event.inline_metadata}")

        elif isinstance(event, BlockMetadataDeltaEvent):
            # Type-safe handling of metadata section
            metadata_count += 1
            metadata_lines.append(event.delta)

            # Metadata-specific field: is_boundary
            boundary_marker = " [BOUNDARY]" if event.is_boundary else ""
            print(f"[META]   Line {event.current_line}: {event.delta!r}{boundary_marker}")

        elif isinstance(event, BlockContentDeltaEvent):
            # Type-safe handling of content section
            content_count += 1
            content_lines.append(event.delta)
            print(f"[CONTENT] Line {event.current_line}: {event.delta!r}")
            print(f"          Accumulated size: {event.accumulated_size} bytes")

        # Handle completion
        elif isinstance(event, BlockEndEvent):
            print()
            print(f"[END] Block completed: {event.block_id}")
            print(f"      Lines: {event.start_line}-{event.end_line}")
            print(f"      Type: {event.block_type}")

        elif isinstance(event, TextContentEvent):
            # Regular text outside blocks
            if event.content.strip():
                print(f"[TEXT] {event.content.strip()}")

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Header deltas:   {header_count}")
    print(f"Metadata deltas: {metadata_count}")
    print(f"Content deltas:  {content_count}")
    print()
    print("Benefits of section-specific events:")
    print("1. Type safety - isinstance() checks work without string comparisons")
    print("2. Unique fields - is_boundary for metadata, inline_metadata for header")
    print("3. Clear intent - handler code clearly shows which section is processed")


if __name__ == "__main__":
    asyncio.run(main())
