"""Example demonstrating the minimal API with no custom models."""

import asyncio
from textwrap import dedent
from typing import TYPE_CHECKING

from hother.streamblocks import Registry, StreamBlockProcessor
from hother.streamblocks.core.processor import ProcessorConfig
from hother.streamblocks.core.types import BlockEndEvent, BlockErrorEvent, TextContentEvent
from hother.streamblocks_examples.helpers.simulator import simulated_stream

if TYPE_CHECKING:
    from hother.streamblocks.core.models import ExtractedBlock
    from hother.streamblocks.core.types import BaseContent, BaseMetadata


async def main() -> None:
    """Main example function."""
    # Create syntax with NO custom models - uses BaseMetadata and BaseContent
    registry = Registry()

    # Create processor with the registry
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

                print("\n[BLOCK] Extracted:")
                print(block.model_dump_json(indent=2))

        elif isinstance(event, BlockErrorEvent):
            # Block rejected
            print(f"\n[REJECT] {event.reason}")

    print("\n" + "-" * 60)
    print(f"Total blocks extracted: {len(blocks_extracted)}")

    # Show all extracted blocks
    print("\nExtracted blocks (full details):")
    for i, block in enumerate(blocks_extracted, 1):
        print(f"\n--- Block {i} ---")
        print(block.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
