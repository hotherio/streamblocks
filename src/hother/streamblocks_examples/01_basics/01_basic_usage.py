"""Basic usage example for StreamBlocks."""

import asyncio
from textwrap import dedent
from typing import TYPE_CHECKING

from hother.streamblocks import Registry, StreamBlockProcessor
from hother.streamblocks.core.models import ExtractedBlock
from hother.streamblocks.core.types import (
    BlockContentDeltaEvent,
    BlockEndEvent,
    BlockErrorEvent,
    BlockHeaderDeltaEvent,
    BlockMetadataDeltaEvent,
    TextContentEvent,
)
from hother.streamblocks_examples.blocks.agent.files import (
    FileOperations,
    FileOperationsContent,
    FileOperationsMetadata,
)
from hother.streamblocks_examples.helpers.simulator import simulated_stream

if TYPE_CHECKING:
    from hother.streamblocks.core.types import BaseContent, BaseMetadata


async def main() -> None:
    """Main example function."""

    # Create type-specific registry and register block
    registry = Registry()

    # Add a custom validator
    def no_root_delete(block: ExtractedBlock[FileOperationsMetadata, FileOperationsContent]) -> bool:
        """Don't allow deleting files from root directory."""
        return all(not (op.action == "delete" and op.path.startswith("/")) for op in block.content.operations)

    registry.register("files_operations", FileOperations, validators=[no_root_delete])

    # Create processor with config
    from hother.streamblocks.core.processor import ProcessorConfig

    config = ProcessorConfig(lines_buffer=5)
    processor = StreamBlockProcessor(registry, config=config)

    # Example text with multiple blocks
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

    # Process stream
    print("Processing stream...")
    print("-" * 60)

    blocks_extracted: list[ExtractedBlock[BaseMetadata, BaseContent]] = []

    async for event in processor.process_stream(simulated_stream(text)):
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
                print("\n[BLOCK] Extracted:")
                print(block.model_dump_json(indent=2))

        elif isinstance(event, BlockErrorEvent):
            # Block rejected
            print(f"[REJECT] {event.reason} - {event.syntax}")

    print("-" * 60)
    print(f"\nTotal blocks extracted: {len(blocks_extracted)}")

    # Show all extracted blocks
    print("\nExtracted blocks (full details):")
    for i, block in enumerate(blocks_extracted, 1):
        print(f"\n--- Block {i} ---")
        print(block.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
