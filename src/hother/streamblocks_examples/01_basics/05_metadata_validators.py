#!/usr/bin/env python3
"""Early metadata validation with failure modes."""

# --8<-- [start:imports]
import asyncio
from textwrap import dedent
from typing import Any

from hother.streamblocks import (
    DelimiterFrontmatterSyntax,
    MetadataValidationFailureMode,
    Registry,
    StreamBlockProcessor,
    ValidationResult,
)
from hother.streamblocks.core.types import BlockEndEvent, BlockErrorEvent
from hother.streamblocks_examples.blocks.agent.files import FileOperations
from hother.streamblocks_examples.helpers.simulator import simple_text_stream

# --8<-- [end:imports]


# --8<-- [start:validators]
def validate_required_fields(raw: str, parsed: dict[str, Any] | None) -> ValidationResult:
    """Validate that required metadata fields are present."""
    if not parsed:
        return ValidationResult.failure("No metadata parsed")
    if "id" not in parsed:
        return ValidationResult.failure("Missing required field: id")
    return ValidationResult.success()


def validate_id_format(raw: str, parsed: dict[str, Any] | None) -> ValidationResult:
    """Validate that ID follows naming convention."""
    if not parsed:
        return ValidationResult.success()  # Let other validator handle this
    block_id = parsed.get("id", "")
    if not block_id.startswith("ops-"):
        return ValidationResult.failure(f"ID must start with 'ops-', got: {block_id}")
    return ValidationResult.success()


# --8<-- [end:validators]


# --8<-- [start:main]
async def main() -> None:
    """Demonstrate metadata validation with different failure modes."""
    syntax = DelimiterFrontmatterSyntax()

    # --8<-- [start:abort_mode]
    # Mode 1: ABORT_BLOCK (default) - stop processing on validation failure
    registry = Registry(
        syntax=syntax,
        metadata_failure_mode=MetadataValidationFailureMode.ABORT_BLOCK,
    )
    registry.register("files_operations", FileOperations)
    registry.add_metadata_validator("files_operations", validate_id_format)
    processor = StreamBlockProcessor(registry)

    # This block has an invalid ID (doesn't start with 'ops-')
    text = dedent("""
        !!start
        ---
        id: invalid-id
        block_type: files_operations
        ---
        src/main.py:C
        !!end
    """).strip()

    print("=== ABORT_BLOCK mode ===")
    async for event in processor.process_stream(simple_text_stream(text)):
        if isinstance(event, BlockErrorEvent):
            print(f"Error: {event.reason}")
        elif isinstance(event, BlockEndEvent):
            print(f"Block extracted: {event.get_block()}")
    # --8<-- [end:abort_mode]

    # --8<-- [start:valid_block]
    # Valid block with correct ID format
    valid_text = dedent("""
        !!start
        ---
        id: ops-001
        block_type: files_operations
        ---
        src/main.py:C
        !!end
    """).strip()

    print("\n=== Valid block ===")
    async for event in processor.process_stream(simple_text_stream(valid_text)):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block:
                print("Block extracted:")
                print(block.model_dump_json(indent=2))
    # --8<-- [end:valid_block]


# --8<-- [end:main]


if __name__ == "__main__":
    asyncio.run(main())
