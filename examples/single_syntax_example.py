"""Example demonstrating single syntax processing with StreamBlocks.

This example shows the new type-specific registry design where each
processor handles exactly one syntax type.
"""

import asyncio
from collections.abc import AsyncIterator

from hother.streamblocks import (
    DelimiterPreambleSyntax,
    EventType,
    Registry,
    StreamBlockProcessor,
)
from hother.streamblocks.blocks import (
    FileOperationsContent,
    FileOperationsMetadata,
)


async def file_operations_stream() -> AsyncIterator[str]:
    """Stream with file operations blocks."""
    text = """
In this document, we'll demonstrate how StreamBlocks processes
blocks using a single syntax type per processor.

First, let's create some files:

!!files01:files_operations
README.md:C
docs/getting-started.md:C
docs/api-reference.md:C
src/__init__.py:C
!!end

Now let's clean up some old files:

!!cleanup01:files_operations:critical
old_module.py:D
deprecated.py:D
legacy_tests.py:D
!!end

And finally, let's update some existing files:

!!update01:files_operations
src/main.py:E
src/utils.py:E
tests/test_main.py:E
!!end

That's it! Each processor handles one syntax type efficiently.
"""

    # Simulate streaming
    chunk_size = 50
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        yield chunk
        await asyncio.sleep(0.008)


async def main() -> None:
    """Main example function."""
    print("=== Single Syntax Processing Example ===\n")

    # Create syntax for file operations
    file_ops_syntax = DelimiterPreambleSyntax(
        name="files_operations_syntax",
        metadata_class=FileOperationsMetadata,
        content_class=FileOperationsContent,
    )

    # Create type-specific registry
    registry = Registry(file_ops_syntax)

    # Add a validator for critical operations
    def validate_critical_ops(metadata: FileOperationsMetadata, content: FileOperationsContent) -> bool:
        """Extra validation for critical operations."""
        if hasattr(metadata, "param_0") and metadata.param_0 == "critical":
            # Don't allow deleting system files in critical ops
            for op in content.operations:
                if op.action == "delete" and op.path.startswith("/"):
                    return False
        return True

    registry.add_validator("files_operations", validate_critical_ops)

    # Create processor
    processor = StreamBlockProcessor(registry, lines_buffer=10)

    # Process stream
    print("Processing file operations stream...\n")

    blocks_extracted = []

    async for event in processor.process_stream(file_operations_stream()):
        if event.type == EventType.RAW_TEXT:
            # Show text
            if event.data.strip():
                text = event.data.strip()
                if len(text) > 60:
                    text = text[:57] + "..."
                print(f"[TEXT] {text}")

        elif event.type == EventType.BLOCK_EXTRACTED:
            # Complete block extracted
            block = event.block
            blocks_extracted.append(block)

            print(f"\n{'=' * 60}")
            print(f"[BLOCK] {block.metadata.id} ({block.metadata.block_type})")
            print(f"        Syntax: {block.syntax_name}")

            # Access operations directly from data
            creates = [op for op in block.data.operations if op.action == "create"]
            edits = [op for op in block.data.operations if op.action == "edit"]
            deletes = [op for op in block.data.operations if op.action == "delete"]

            print(f"        Total operations: {len(block.data.operations)}")

            if creates:
                print(f"\n        ✅ CREATE ({len(creates)} files):")
                for op in creates[:3]:
                    print(f"           + {op.path}")
                if len(creates) > 3:
                    print(f"           ... and {len(creates) - 3} more")

            if edits:
                print(f"\n        ✏️  EDIT ({len(edits)} files):")
                for op in edits[:3]:
                    print(f"           ~ {op.path}")

            if deletes:
                print(f"\n        ❌ DELETE ({len(deletes)} files):")
                for op in deletes[:3]:
                    print(f"           - {op.path}")

            # Check for extra params
            if hasattr(block.metadata, "param_0"):
                print(f"\n        Priority: {block.metadata.param_0}")

            print(f"{'=' * 60}\n")

        elif event.type == EventType.BLOCK_REJECTED:
            # Block rejected
            reason = event.content["reason"]
            print(f"\n[REJECT] {reason}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print(f"  Total blocks extracted: {len(blocks_extracted)}")


if __name__ == "__main__":
    asyncio.run(main())
