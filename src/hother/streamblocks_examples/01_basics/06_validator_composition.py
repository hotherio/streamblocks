#!/usr/bin/env python3
"""Chaining multiple validators: metadata, content, and general."""

# --8<-- [start:imports]
import asyncio
from textwrap import dedent
from typing import Any

from hother.streamblocks import (
    DelimiterFrontmatterSyntax,
    Registry,
    StreamBlockProcessor,
    ValidationResult,
)
from hother.streamblocks.core.models import ExtractedBlock
from hother.streamblocks.core.types import BlockEndEvent
from hother.streamblocks_examples.blocks.agent.files import FileOperations

# --8<-- [end:imports]


# --8<-- [start:metadata_validators]
def validate_has_description(raw: str, parsed: dict[str, Any] | None) -> ValidationResult:
    """First metadata validator: check for description."""
    if parsed and "description" not in parsed:
        return ValidationResult.failure("Missing 'description' in metadata")
    return ValidationResult.success()


def validate_id_length(raw: str, parsed: dict[str, Any] | None) -> ValidationResult:
    """Second metadata validator: check ID length."""
    min_id_length = 3
    if parsed:
        block_id = str(parsed.get("id", ""))
        if len(block_id) < min_id_length:
            return ValidationResult.failure(f"ID too short: {len(block_id)} < {min_id_length}")
    return ValidationResult.success()


# --8<-- [end:metadata_validators]


# --8<-- [start:content_validators]
def validate_has_operations(raw: str, parsed: dict[str, Any] | None) -> ValidationResult:
    """Content validator: ensure there are operations."""
    if not raw.strip():
        return ValidationResult.failure("Content is empty")
    return ValidationResult.success()


def validate_no_delete(raw: str, parsed: dict[str, Any] | None) -> ValidationResult:
    """Content validator: prevent delete operations."""
    if ":D" in raw.upper():
        return ValidationResult.failure("Delete operations not allowed")
    return ValidationResult.success()


# --8<-- [end:content_validators]


# --8<-- [start:general_validators]
def validate_max_operations(block: ExtractedBlock[Any, Any]) -> bool:
    """General validator: limit number of operations."""
    max_ops = 5
    if hasattr(block.content, "operations"):
        return len(block.content.operations) <= max_ops
    return True


# --8<-- [end:general_validators]


# --8<-- [start:main]
async def main() -> None:
    """Demonstrate validator chaining."""
    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)

    # --8<-- [start:register_validators]
    # Register metadata validators (run in order, first failure stops)
    registry.add_metadata_validator("files_operations", validate_has_description)
    registry.add_metadata_validator("files_operations", validate_id_length)

    # Register content validators (run in order, first failure stops)
    registry.add_content_validator("files_operations", validate_has_operations)
    registry.add_content_validator("files_operations", validate_no_delete)

    # Register general validator (runs after full block extraction)
    registry.add_validator("files_operations", validate_max_operations)
    # --8<-- [end:register_validators]

    processor = StreamBlockProcessor(registry)

    # --8<-- [start:test]
    # Valid block that passes all validators
    text = dedent("""
        !!start
        ---
        id: ops001
        block_type: files_operations
        description: Create new source files
        ---
        src/main.py:C
        src/utils.py:C
        !!end
    """).strip()

    from hother.streamblocks_examples.helpers.simulator import simple_text_stream

    print("=== Validator chain test ===")
    async for event in processor.process_stream(simple_text_stream(text)):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block:
                print("Block passed all validators!")
                print(block.model_dump_json(indent=2))
    # --8<-- [end:test]


# --8<-- [end:main]


if __name__ == "__main__":
    asyncio.run(main())
