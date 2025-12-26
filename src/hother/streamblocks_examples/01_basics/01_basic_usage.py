"""Basic usage example for StreamBlocks."""

import asyncio
from collections.abc import AsyncIterator
from textwrap import dedent
from typing import TYPE_CHECKING

from examples.blocks.agent.files import FileOperations, FileOperationsContent, FileOperationsMetadata
from hother.streamblocks import DelimiterPreambleSyntax, Registry, StreamBlockProcessor
from hother.streamblocks.core.models import ExtractedBlock
from hother.streamblocks.core.types import (
    BlockContentDeltaEvent,
    BlockEndEvent,
    BlockErrorEvent,
    BlockHeaderDeltaEvent,
    BlockMetadataDeltaEvent,
    TextContentEvent,
)

if TYPE_CHECKING:
    from hother.streamblocks.core.types import BaseContent, BaseMetadata


async def example_stream() -> AsyncIterator[str]:
    """Example stream with multiple blocks."""
    text = dedent("""
        This is some introductory text that will be passed through as raw text.

        !!file01:files_operations
        src/main.py:C
        src/utils.py:C
        tests/test_main.py:C
        !!end

        Here's some text between blocks.

        !!file02:files_operations:urgent
        config.yaml:C
        README.md:C
        old_file.py:D
        !!end

        And some final text after all blocks.
    """)

    # Simulate chunk-based streaming (more realistic than line-by-line)
    chunk_size = 50
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        yield chunk
        await asyncio.sleep(0.01)  # Simulate network delay


async def main() -> None:
    """Main example function."""
    # Create delimiter preamble syntax
    syntax = DelimiterPreambleSyntax()

    # Create type-specific registry and register block
    registry = Registry(syntax=syntax)

    # Add a custom validator
    def no_root_delete(block: ExtractedBlock[FileOperationsMetadata, FileOperationsContent]) -> bool:
        """Don't allow deleting files from root directory."""
        return all(not (op.action == "delete" and op.path.startswith("/")) for op in block.content.operations)

    registry.register("files_operations", FileOperations, validators=[no_root_delete])

    # Create processor with config
    from hother.streamblocks.core.processor import ProcessorConfig

    config = ProcessorConfig(lines_buffer=5)
    processor = StreamBlockProcessor(registry, config=config)

    # Process stream
    print("Processing stream...")
    print("-" * 60)

    blocks_extracted: list[ExtractedBlock[BaseMetadata, BaseContent]] = []

    async for event in processor.process_stream(example_stream()):
        if isinstance(event, TextContentEvent):
            # Raw text passed through
            if event.content.strip():  # Skip empty lines for cleaner output
                print(f"[TEXT] {event.content.strip()}")

        elif isinstance(event, (BlockHeaderDeltaEvent, BlockMetadataDeltaEvent, BlockContentDeltaEvent)):
            # Partial block update
            section = event.type.value.replace("BLOCK_", "").replace("_DELTA", "").lower()
            print(f"[DELTA] {section} - {event.delta.strip()}")

        elif isinstance(event, BlockEndEvent):
            # Complete block extracted
            block = event.get_block()
            if block is not None:
                blocks_extracted.append(block)
                print(f"[BLOCK] Extracted: {block.metadata.id} ({block.syntax_name})")

                # Type narrow to FileOperationsContent for specific access
                if isinstance(block.content, FileOperationsContent):
                    print("        Operations:")
                    for op in block.content.operations:
                        print(f"          - {op.action}: {op.path}")

        elif isinstance(event, BlockErrorEvent):
            # Block rejected
            print(f"[REJECT] {event.reason} - {event.syntax}")

    print("-" * 60)
    print(f"\nTotal blocks extracted: {len(blocks_extracted)}")
    for block in blocks_extracted:
        print(block)

    # Show metadata from blocks
    print("\nBlock metadata:")
    for block in blocks_extracted:
        print(f"  - {block.metadata.id}: {block.metadata.block_type}")
        # Check for dynamic extra parameters (e.g., param_0 from preamble)
        param_0 = getattr(block.metadata, "param_0", None)
        if param_0 is not None:
            print(f"    Extra param: {param_0}")


if __name__ == "__main__":
    asyncio.run(main())
