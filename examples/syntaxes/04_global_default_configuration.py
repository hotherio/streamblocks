"""Example demonstrating global default syntax configuration.

This example shows how setting a global default syntax simplifies applications
that use multiple registries. Set the default once at startup, then create
registries without specifying the syntax argument.
"""

import asyncio
from collections.abc import AsyncIterator
from typing import Literal

from pydantic import Field

import hother.streamblocks as sb
from hother.streamblocks.core.models import Block, ExtractedBlock
from hother.streamblocks.core.types import BaseContent, BaseMetadata

# =============================================================================
# Application Setup - Set Global Default ONCE
# =============================================================================

# This is typically done at application startup (e.g., in __init__.py or main.py)
sb.set_default_syntax(sb.Syntax.DELIMITER_PREAMBLE)

print("✓ Global default syntax set to DELIMITER_PREAMBLE")
print("  All registries will use !!id:type format by default\n")


# =============================================================================
# Define Block Types for Different Domains
# =============================================================================


class TaskMetadata(BaseMetadata):
    """Metadata for task blocks."""

    id: str
    block_type: Literal["task"] = "task"  # type: ignore[assignment]


class TaskContent(BaseContent):
    """Content for task blocks."""

    description: str = ""

    @classmethod
    def parse(cls, raw_text: str) -> "TaskContent":
        """Parse task content."""
        return cls(raw_content=raw_text, description=raw_text.strip())


TaskBlock = Block[TaskMetadata, TaskContent]


class NoteMetadata(BaseMetadata):
    """Metadata for note blocks."""

    id: str
    block_type: Literal["note"] = "note"  # type: ignore[assignment]


class NoteContent(BaseContent):
    """Content for note blocks."""

    text: str = ""

    @classmethod
    def parse(cls, raw_text: str) -> "NoteContent":
        """Parse note content."""
        return cls(raw_content=raw_text, text=raw_text.strip())


NoteBlock = Block[NoteMetadata, NoteContent]


# =============================================================================
# Stream Generators
# =============================================================================


async def tasks_stream() -> AsyncIterator[str]:
    """Stream with task blocks."""
    text = """
Here are some tasks:

!!t01:task
Implement authentication system
!!end

!!t02:task
Write unit tests
!!end
"""
    for char in text:
        yield char
        await asyncio.sleep(0.001)


async def notes_stream() -> AsyncIterator[str]:
    """Stream with note blocks."""
    text = """
Some notes:

!!n01:note
Remember to review the pull requests
!!end

!!n02:note
Team meeting tomorrow at 10am
!!end
"""
    for char in text:
        yield char
        await asyncio.sleep(0.001)


# =============================================================================
# Processing Functions
# =============================================================================


async def process_tasks() -> list[ExtractedBlock[BaseMetadata, BaseContent]]:
    """Process tasks using a registry WITHOUT specifying syntax."""
    # No syntax argument - uses global default!
    registry = sb.Registry()
    registry.register("task", TaskBlock)

    processor = sb.StreamBlockProcessor(registry)

    blocks: list[ExtractedBlock[BaseMetadata, BaseContent]] = []
    async for event in processor.process_stream(tasks_stream()):
        if event.type == sb.EventType.BLOCK_EXTRACTED:
            blocks.append(event.block)

    return blocks


async def process_notes() -> list[ExtractedBlock[BaseMetadata, BaseContent]]:
    """Process notes using a registry WITHOUT specifying syntax."""
    # No syntax argument - uses global default!
    registry = sb.Registry()
    registry.register("note", NoteBlock)

    processor = sb.StreamBlockProcessor(registry)

    blocks: list[ExtractedBlock[BaseMetadata, BaseContent]] = []
    async for event in processor.process_stream(notes_stream()):
        if event.type == sb.EventType.BLOCK_EXTRACTED:
            blocks.append(event.block)

    return blocks


# =============================================================================
# Main
# =============================================================================


async def main() -> None:
    """Main example function."""
    print("=== Global Default Syntax Configuration ===\n")

    # Process tasks (uses global default)
    print("Processing tasks (using global default DELIMITER_PREAMBLE)...")
    task_blocks = await process_tasks()
    print(f"✓ Extracted {len(task_blocks)} task blocks")
    for block in task_blocks:
        if isinstance(block.metadata, TaskMetadata):
            print(f"  - {block.metadata.id}: {block.content.raw_content[:40]}...")

    print()

    # Process notes (uses global default)
    print("Processing notes (using global default DELIMITER_PREAMBLE)...")
    note_blocks = await process_notes()
    print(f"✓ Extracted {len(note_blocks)} note blocks")
    for block in note_blocks:
        if isinstance(block.metadata, NoteMetadata):
            print(f"  - {block.metadata.id}: {block.content.raw_content[:40]}...")

    print()

    # Show that we can still override for special cases
    print("Creating a special registry with explicit syntax override...")
    special_registry = sb.Registry(syntax=sb.Syntax.DELIMITER_FRONTMATTER)
    print(f"✓ Special registry uses: {special_registry.syntax.__class__.__name__}")

    print("\n" + "=" * 60)
    print("KEY BENEFITS:")
    print("=" * 60)
    print("✓ Set syntax ONCE at application startup")
    print("✓ Create registries WITHOUT syntax argument")
    print("✓ Ensures consistency across all processors")
    print("✓ Easy to change syntax for entire application")
    print("✓ Can still override for special cases")
    print()
    print("Resolution priority:")
    print("  1. Explicit syntax argument (highest)")
    print("  2. Global default (set with set_default_syntax)")
    print("  3. System default (DELIMITER_FRONTMATTER)")


if __name__ == "__main__":
    asyncio.run(main())
