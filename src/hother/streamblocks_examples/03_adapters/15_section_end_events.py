#!/usr/bin/env python3
"""Example 15: Section End Events.

This example demonstrates the section end events feature which enables:
- Early processing of completed sections
- Section-specific validation before block completion
- State management for UIs
- Streaming optimization (early resource release)

Section end events are emitted when sections complete:
- BlockMetadataEndEvent: When metadata section ends (before content begins)
- BlockContentEndEvent: When content section ends (before BlockEndEvent)
"""

import asyncio

from hother.streamblocks import (
    BlockContentEndEvent,
    BlockEndEvent,
    BlockMetadataEndEvent,
    BlockStartEvent,
    DelimiterFrontmatterSyntax,
    DelimiterPreambleSyntax,
    MetadataValidationFailureMode,
    Registry,
    StreamBlockProcessor,
    ValidationResult,
)
from hother.streamblocks.core.processor import ProcessorConfig
from hother.streamblocks_examples.blocks.agent.files import FileOperations
from hother.streamblocks_examples.helpers.simulator import simulated_stream


async def example_basic_section_events() -> None:
    """Example 1: Basic section end events."""
    print("=" * 60)
    print("Example 1: Basic Section End Events (Preamble Syntax)")
    print("=" * 60)
    print()

    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)

    # Section end events are enabled by default
    processor = StreamBlockProcessor(registry)

    text = "".join(
        [
            "Starting project...\n",
            "!!project:files_operations\n",
            "src/main.py:C\n",
            "src/utils.py:C\n",
            "!!end\n",
            "Done!\n",
        ]
    )

    print("Processing stream with section end events enabled:")
    print()

    async for event in processor.process_stream(simulated_stream(text, preset="fast")):
        if isinstance(event, BlockStartEvent):
            print(f"  [BlockStart] Block opened: {event.syntax}")
        elif isinstance(event, BlockContentEndEvent):
            print("  [ContentEnd] Content section complete")
            print(f"    - Raw content length: {len(event.raw_content)} chars")
            print(f"    - Parsed: {event.parsed_content}")
            print(f"    - Validation passed: {event.validation_passed}")
        elif isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block:
                print(f"  [BlockEnd] Block extracted: {event.block_type}")
                print(block.model_dump_json(indent=2))

    print()


async def example_disabled_section_events() -> None:
    """Example 2: Section end events disabled."""
    print("=" * 60)
    print("Example 2: Section End Events Disabled (Opt-out)")
    print("=" * 60)
    print()

    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)

    # Disable section end events for maximum performance
    config = ProcessorConfig(emit_section_end_events=False)  # Opt-out
    processor = StreamBlockProcessor(registry, config=config)

    text = "".join(
        [
            "!!project:files_operations\n",
            "src/main.py:C\n",
            "!!end\n",
        ]
    )

    print("Processing stream with section end events DISABLED:")
    print()

    event_types = []
    async for event in processor.process_stream(simulated_stream(text, preset="fast")):
        event_types.append(type(event).__name__)
        if isinstance(event, BlockEndEvent):
            print("  [BlockEnd] Block extracted (no ContentEnd event)")

    print()
    print(f"Event types received: {event_types}")
    print("Notice: No BlockContentEndEvent when disabled")
    print()


async def example_frontmatter_metadata_events() -> None:
    """Example 3: Metadata end events with frontmatter syntax."""
    print("=" * 60)
    print("Example 3: Metadata End Events (Frontmatter Syntax)")
    print("=" * 60)
    print()

    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)

    processor = StreamBlockProcessor(registry)

    text = "".join(
        [
            "!!start\n",
            "---\n",
            "id: my_block\n",
            "block_type: files_operations\n",
            "---\n",  # This triggers BlockMetadataEndEvent
            "src/main.py:C\n",
            "!!end\n",
        ]
    )

    print("Processing stream with YAML frontmatter:")
    print()

    async for event in processor.process_stream(simulated_stream(text, preset="fast")):
        if isinstance(event, BlockStartEvent):
            print("  [BlockStart] Block opened")
        elif isinstance(event, BlockMetadataEndEvent):
            print("  [MetadataEnd] Metadata section complete!")
            print(f"    - Parsed metadata: {event.parsed_metadata}")
            print(f"    - Validation passed: {event.validation_passed}")
        elif isinstance(event, BlockContentEndEvent):
            print("  [ContentEnd] Content section complete")
        elif isinstance(event, BlockEndEvent):
            print(f"  [BlockEnd] Block extracted: {event.block_type}")

    print()


async def example_early_validation() -> None:
    """Example 4: Early validation with section end events."""
    print("=" * 60)
    print("Example 4: Early Validation with Section End Events")
    print("=" * 60)
    print()

    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(
        syntax=syntax,
        # Abort block on metadata validation failure
        metadata_failure_mode=MetadataValidationFailureMode.ABORT_BLOCK,
    )
    registry.register("files_operations", FileOperations)

    # Add a metadata validator that requires specific fields
    def validate_metadata(raw: str, parsed: dict | None) -> ValidationResult:
        if not parsed:
            return ValidationResult.failure("No metadata parsed")
        if parsed.get("id") == "forbidden":
            return ValidationResult.failure("ID 'forbidden' is not allowed")
        return ValidationResult.success()

    registry.add_metadata_validator("files_operations", validate_metadata)

    processor = StreamBlockProcessor(registry)

    print("Processing block with forbidden ID (will fail validation):")
    print()

    # This block will fail validation
    text = "".join(
        [
            "!!start\n",
            "---\n",
            "id: forbidden\n",
            "block_type: files_operations\n",
            "---\n",
            "src/main.py:C\n",
            "!!end\n",
        ]
    )

    async for event in processor.process_stream(simulated_stream(text, preset="fast")):
        if isinstance(event, BlockMetadataEndEvent):
            print(f"  [MetadataEnd] Validation passed: {event.validation_passed}")
            if not event.validation_passed:
                print(f"    Error: {event.validation_error}")
        elif hasattr(event, "error_code"):
            print("  [Error] Block aborted due to validation failure")

    print()
    print("Processing block with valid ID (will pass validation):")
    print()

    # This block will pass validation
    text_valid = "".join(
        [
            "!!start\n",
            "---\n",
            "id: allowed\n",
            "block_type: files_operations\n",
            "---\n",
            "src/main.py:C\n",
            "!!end\n",
        ]
    )

    # Reset processor
    processor = StreamBlockProcessor(registry)

    async for event in processor.process_stream(simulated_stream(text_valid, preset="fast")):
        if isinstance(event, BlockMetadataEndEvent):
            print(f"  [MetadataEnd] Validation passed: {event.validation_passed}")
        elif isinstance(event, BlockEndEvent):
            print("  [BlockEnd] Block extracted successfully!")

    print()


async def main() -> None:
    """Run all examples."""
    print()
    print("Section End Events Examples")
    print()

    await example_basic_section_events()
    await example_disabled_section_events()
    await example_frontmatter_metadata_events()
    await example_early_validation()

    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print()
    print("Section end events enable:")
    print("  - Early processing of completed sections")
    print("  - Section-specific validation (abort early on failure)")
    print("  - UI state management (update UI when sections complete)")
    print("  - Streaming optimization (release resources early)")
    print()
    print("Configuration:")
    print("  - emit_section_end_events=True (default)")
    print("  - emit_section_end_events=False (opt-out for performance)")
    print()


if __name__ == "__main__":
    asyncio.run(main())
