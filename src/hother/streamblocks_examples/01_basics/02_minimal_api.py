"""Example demonstrating the minimal API with no custom models."""

import asyncio
from textwrap import dedent
from typing import TYPE_CHECKING

from hother.streamblocks import (
    DelimiterPreambleSyntax,
    Registry,
    StreamBlockProcessor,
)
from hother.streamblocks.core.types import BlockEndEvent, BlockErrorEvent, TextContentEvent
from hother.streamblocks_examples.helpers.simulator import simulated_stream

if TYPE_CHECKING:
    from hother.streamblocks.core.models import ExtractedBlock
    from hother.streamblocks.core.types import BaseContent, BaseMetadata


async def main() -> None:
    """Main example function."""
    # Create syntax with NO custom models - uses BaseMetadata and BaseContent
    syntax = DelimiterPreambleSyntax()

    # Create type-specific registry
    registry = Registry(syntax=syntax)

    # Create processor with the registry
    from hother.streamblocks.core.processor import ProcessorConfig

    config = ProcessorConfig(lines_buffer=5)
    processor = StreamBlockProcessor(registry, config=config)

    # Example text with simple blocks
    text = dedent("""
        This is a document with some blocks using the minimal API.

        !!note01:notes
        This is a simple note block.
        No custom models needed!
        The library handles everything.
        !!end

        Some text between blocks.

        !!todo01:tasks
        - Buy groceries
        - Call mom
        - Finish the report
        !!end

        !!code01:snippets
        def hello():
            print("Hello, world!")
        !!end

        That's all folks!
    """)

    # Process stream
    print("Processing with minimal API...")
    print("-" * 60)

    blocks_extracted: list[ExtractedBlock[BaseMetadata, BaseContent]] = []

    async for event in processor.process_stream(simulated_stream(text)):
        if isinstance(event, TextContentEvent):
            # Raw text passed through
            if event.content.strip():
                print(f"[TEXT] {event.content.strip()}")

        elif isinstance(event, BlockEndEvent):
            # Complete block extracted
            block = event.get_block()
            if block is not None:
                blocks_extracted.append(block)

                print("\n[BLOCK] Extracted!")
                print(f"  ID: {block.metadata.id}")
                print(f"  Type: {block.metadata.block_type}")
                print(f"  Raw content preview: {block.content.raw_content[:50]}...")

                # All blocks have raw_content automatically
                lines = block.content.raw_content.split("\n")
                print(f"  Content lines: {len(lines)}")

        elif isinstance(event, BlockErrorEvent):
            # Block rejected
            print(f"\n[REJECT] {event.reason}")

    print("\n" + "-" * 60)
    print(f"Total blocks extracted: {len(blocks_extracted)}")

    # Summary
    print("\nBlock summary:")
    for i, block in enumerate(blocks_extracted, 1):
        print(f"  {i}. {block.metadata.id} ({block.metadata.block_type})")

    print("\n✓ Simple single-syntax processing - no custom models needed!")


if __name__ == "__main__":
    asyncio.run(main())
