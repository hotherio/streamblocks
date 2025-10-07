"""Basic usage example for StreamBlocks."""

import asyncio
from collections.abc import AsyncIterator

from hother.streamblocks import (
    DelimiterPreambleSyntax,
    EventType,
    Registry,
    StreamBlockProcessor,
)
from hother.streamblocks.content import FileOperationsContent, FileOperationsMetadata


async def example_stream() -> AsyncIterator[str]:
    """Example stream with multiple blocks."""
    text = """
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
"""

    # Simulate chunk-based streaming (more realistic than line-by-line)
    chunk_size = 50
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        yield chunk
        await asyncio.sleep(0.01)  # Simulate network delay


async def main() -> None:
    """Main example function."""
    # Create delimiter preamble syntax
    syntax = DelimiterPreambleSyntax(
        name="files_operations_syntax",
        metadata_class=FileOperationsMetadata,
        content_class=FileOperationsContent,
    )

    # Create type-specific registry
    registry = Registry(syntax)

    # Add a custom validator
    def no_root_delete(metadata: FileOperationsMetadata, content: FileOperationsContent) -> bool:
        """Don't allow deleting files from root directory."""
        return all(not (op.action == "delete" and op.path.startswith("/")) for op in content.operations)

    registry.add_validator("files_operations", no_root_delete)

    # Create processor
    processor = StreamBlockProcessor(registry, lines_buffer=5)

    # Process stream
    print("Processing stream...")
    print("-" * 60)

    blocks_extracted = []

    async for event in processor.process_stream(example_stream()):
        if event.type == EventType.RAW_TEXT:
            # Raw text passed through
            if event.data.strip():  # Skip empty lines for cleaner output
                print(f"[TEXT] {event.data.strip()}")

        elif event.type == EventType.BLOCK_DELTA:
            # Partial block update
            print(f"[DELTA] {event.metadata['syntax']} - {event.data.strip()}")

        elif event.type == EventType.BLOCK_EXTRACTED:
            # Complete block extracted
            block = event.metadata["extracted_block"]
            blocks_extracted.append(block)
            print(f"[BLOCK] Extracted: {block.metadata.id} ({block.syntax_name})")
            print("        Operations:")
            for op in block.content.operations:
                print(f"          - {op.action}: {op.path}")

        elif event.type == EventType.BLOCK_REJECTED:
            # Block rejected
            print(f"[REJECT] {event.metadata['reason']} - {event.metadata['syntax']}")

    print("-" * 60)
    print(f"\nTotal blocks extracted: {len(blocks_extracted)}")

    # Show metadata from blocks
    print("\nBlock metadata:")
    for block in blocks_extracted:
        print(f"  - {block.metadata.id}: {block.metadata.block_type}")
        if hasattr(block.metadata, "param_0"):
            print(f"    Extra param: {block.metadata.param_0}")


if __name__ == "__main__":
    asyncio.run(main())
