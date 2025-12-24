"""Structured Error Handling Example.

This example demonstrates how to access detailed error information
from BlockRejectedEvent, including the original exception objects.
"""

import asyncio
import logging
from typing import TYPE_CHECKING

import yaml
from pydantic import ValidationError

from hother.streamblocks import Registry, StreamBlockProcessor
from hother.streamblocks.core.types import BlockEndEvent, BlockErrorEvent, TextContentEvent
from hother.streamblocks.syntaxes.models import Syntax

if TYPE_CHECKING:
    from hother.streamblocks.core.models import ExtractedBlock
    from hother.streamblocks.core.types import BaseContent, BaseMetadata


async def main() -> None:
    """Demonstrate structured error handling."""
    # Suppress library logging to stderr (we handle errors programmatically)
    logging.getLogger("hother.streamblocks").setLevel(logging.CRITICAL)

    # Setup registry with basic syntax - no custom block types needed
    registry = Registry(
        syntax=Syntax.DELIMITER_FRONTMATTER,
    )

    # Create processor
    processor = StreamBlockProcessor(registry)

    # Test stream with various error scenarios
    test_stream = """
Some normal text.

!!start
---
id: valid_block
block_type: task
status: complete
---
This is a valid block with proper YAML metadata.
Everything should parse correctly.
!!end

!!start
---
id: broken_yaml
block_type: config
# Malformed YAML below - unclosed bracket
settings: [option1, option2
priority: high
---
This block has invalid YAML in the metadata section.
The YAML parser will fail with a ScannerError.
!!end

!!start
---
# Missing required 'id' and 'block_type' fields
# These are required by BaseMetadata
description: This will fail validation
---
Content for block with missing metadata fields.
!!end

Some more text at the end.
""".strip()

    async def mock_stream():
        """Yield lines from test stream."""
        for line in test_stream.split("\n"):
            yield line + "\n"
            await asyncio.sleep(0.001)

    # Process stream and handle errors with structured information
    print("=" * 60)
    print("STRUCTURED ERROR HANDLING DEMONSTRATION")
    print("=" * 60)

    extracted_blocks: list[ExtractedBlock[BaseMetadata, BaseContent]] = []
    rejected_blocks: list[BlockErrorEvent[BaseMetadata, BaseContent]] = []

    async for event in processor.process_stream(mock_stream()):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is not None:
                extracted_blocks.append(block)
                print(f"\n✅ EXTRACTED: Block {block.metadata.id}")
                print(f"   Type: {block.metadata.block_type}")
                print(f"   Content length: {len(block.content.raw_content)} chars")

        elif isinstance(event, BlockErrorEvent):
            rejected_blocks.append(event)
            print(f"\n❌ REJECTED: Block at lines {event.start_line}-{event.end_line}")
            print(f"   Syntax: {event.syntax}")
            print(f"   Reason: {event.reason}")

            # Access structured exception information
            if event.exception:
                print(f"   Exception Type: {type(event.exception).__name__}")

                # Handle different exception types differently
                if isinstance(event.exception, yaml.YAMLError):
                    print("   → YAML parsing error detected")
                    # Use getattr for attributes not in type stubs
                    problem = getattr(event.exception, "problem", "Unknown YAML error")
                    print(f"   → Problem: {problem}")
                    problem_mark = getattr(event.exception, "problem_mark", None)
                    if problem_mark is not None:
                        line = getattr(problem_mark, "line", -1)
                        column = getattr(problem_mark, "column", -1)
                        print(f"   → Location: line {line + 1}, column {column + 1}")

                elif isinstance(event.exception, ValidationError):
                    print("   → Pydantic validation error detected")
                    print("   → Missing/invalid fields:")
                    for error in event.exception.errors():
                        field = ".".join(str(loc) for loc in error["loc"])
                        msg = error["msg"]
                        print(f"      • {field}: {msg}")

                elif isinstance(event.exception, TypeError):
                    print("   → Type error detected")
                    print(f"   → Details: {event.exception}")

                else:
                    print(f"   → Other error: {event.exception}")

            # Show block_id if available
            if event.block_id:
                print(f"   Block ID: {event.block_id}")

        elif isinstance(event, TextContentEvent):
            # Normal text outside blocks
            text = event.content.strip()
            if text:
                print(f"📄 TEXT: {text}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Extracted blocks: {len(extracted_blocks)}")
    print(f"Rejected blocks: {len(rejected_blocks)}")

    # Detailed rejection analysis
    if rejected_blocks:
        print("\nRejection Analysis:")
        yaml_errors = sum(1 for e in rejected_blocks if isinstance(e.exception, yaml.YAMLError))
        validation_errors = sum(1 for e in rejected_blocks if isinstance(e.exception, ValidationError))
        other_errors = len(rejected_blocks) - yaml_errors - validation_errors

        print(f"  - YAML parsing errors: {yaml_errors}")
        print(f"  - Validation errors: {validation_errors}")
        print(f"  - Other errors: {other_errors}")


if __name__ == "__main__":
    asyncio.run(main())
