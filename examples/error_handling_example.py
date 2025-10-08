"""Structured Error Handling Example.

This example demonstrates how to access detailed error information
from BlockRejectedEvent, including the original exception objects.
"""

import asyncio

import yaml
from pydantic import ValidationError

from hother.streamblocks import (
    EventType,
    Registry,
    StreamBlockProcessor,
)
from hother.streamblocks.core.types import BaseContent, BaseMetadata
from hother.streamblocks.syntaxes.models import Syntax


async def main() -> None:
    """Demonstrate structured error handling."""
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

    extracted_blocks = []
    rejected_blocks = []

    async for event in processor.process_stream(mock_stream()):
        if event.type == EventType.BLOCK_EXTRACTED:
            block = event.block
            extracted_blocks.append(block)
            print(f"\n✅ EXTRACTED: Block {block.metadata.id}")
            print(f"   Type: {block.metadata.block_type}")
            print(f"   Content length: {len(block.content.raw_content)} chars")

        elif event.type == EventType.BLOCK_REJECTED:
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
                    print(f"   → Problem: {event.exception.problem}")
                    if hasattr(event.exception, "problem_mark"):
                        mark = event.exception.problem_mark
                        print(f"   → Location: line {mark.line + 1}, column {mark.column + 1}")

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

            # Show partial content that was rejected
            preview = event.data[:100].replace("\n", "\\n")
            if len(event.data) > 100:
                preview += "..."
            print(f"   Preview: {preview}")

        elif event.type == EventType.RAW_TEXT:
            # Normal text outside blocks
            text = event.data.strip()
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
