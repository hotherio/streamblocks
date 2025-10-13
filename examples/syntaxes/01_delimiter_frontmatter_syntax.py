"""Example demonstrating DelimiterFrontmatterSyntax with YAML frontmatter.

This example shows how to use the delimiter+frontmatter syntax with simple blocks
that DON'T require custom content parsing. Perfect for beginners learning the syntax format.
"""

import asyncio
from collections.abc import AsyncIterator
from typing import Literal

from pydantic import Field

from hother.streamblocks import DelimiterFrontmatterSyntax, EventType, Registry, StreamBlockProcessor
from hother.streamblocks.core.models import Block, ExtractedBlock
from hother.streamblocks.core.types import BaseContent, BaseMetadata


# Simple content models - NO custom parse() needed!
class NoteMetadata(BaseMetadata):
    """Metadata for note blocks."""

    id: str
    block_type: Literal["note"] = "note"  # type: ignore[assignment]
    title: str = "Untitled Note"
    category: str | None = None
    author: str | None = None
    tags: list[str] = Field(default_factory=list)


class NoteContent(BaseContent):
    """Content for note blocks.

    Uses the default parse() method - just stores raw_content.
    No custom parsing needed!
    """

    # Inherits raw_content field from BaseContent
    # No custom parse() method - uses default implementation


# Create the block type
NoteBlock = Block[NoteMetadata, NoteContent]


async def example_stream() -> AsyncIterator[str]:
    """Example stream with delimiter frontmatter blocks."""
    text = """
Let's create some notes using delimiter+frontmatter syntax.

!!start
---
id: note-001
block_type: note
title: Meeting Notes
category: work
author: alice
tags:
  - planning
  - team
---
Discussed project timeline and deliverables.
Team agreed on MVP scope for Q1.
Next meeting scheduled for next Monday.
!!end

Here's another note with simpler metadata:

!!start
---
id: note-002
block_type: note
title: Quick Reminder
category: personal
---
Remember to review the pull requests.
Update documentation before EOD.
!!end

A technical note with rich metadata:

!!start
---
id: note-003
block_type: note
title: Architecture Decision
category: technical
author: bob
tags:
  - architecture
  - database
  - performance
---
Decided to use PostgreSQL for the main database.
Redis will handle caching layer.
Estimated migration time: 2 weeks.
!!end

Some text between blocks.

!!start
---
id: note-004
block_type: note
title: Code Review Feedback
author: charlie
tags:
  - code-review
---
Great implementation overall!
Consider adding unit tests for edge cases.
Documentation could be more detailed.
!!end

That's all for now!
"""
    # Simulate streaming
    chunk_size = 50
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        yield chunk
        await asyncio.sleep(0.01)


async def main() -> None:
    """Main example function."""
    print("=== DelimiterFrontmatterSyntax Example ===\n")
    print("This example uses SIMPLE blocks with NO custom parsing.")
    print("Content is stored directly in the raw_content field.\n")

    # Create delimiter frontmatter syntax for notes
    # Using standard !!start/!!end delimiters
    note_syntax = DelimiterFrontmatterSyntax(
        start_delimiter="!!start",
        end_delimiter="!!end",
    )

    # Create type-specific registry and register block
    registry = Registry(syntax=note_syntax)
    registry.register("note", NoteBlock)

    # Add a simple validator
    def validate_work_notes(block: ExtractedBlock[NoteMetadata, NoteContent]) -> bool:
        """Work notes should have an author."""
        return not (block.metadata.category == "work" and not block.metadata.author)

    registry.add_validator("note", validate_work_notes)

    # Create processor
    processor = StreamBlockProcessor(registry, lines_buffer=10)

    # Process stream
    print("Processing note blocks...\n")

    blocks_extracted: list[ExtractedBlock[BaseMetadata, BaseContent]] = []

    async for event in processor.process_stream(example_stream()):
        if event.type == EventType.RAW_TEXT:
            # Raw text passed through
            if event.data.strip():
                text = event.data.strip()
                if len(text) > 60:
                    text = text[:57] + "..."
                print(f"[TEXT] {text}")

        elif event.type == EventType.BLOCK_EXTRACTED:
            # Complete block extracted
            block = event.block
            blocks_extracted.append(block)

            # Type narrow to NoteMetadata and NoteContent for specific access
            if isinstance(block.metadata, NoteMetadata) and isinstance(block.content, NoteContent):
                metadata = block.metadata
                content = block.content

                print(f"\n{'=' * 60}")
                print(f"[NOTE] {metadata.id} - {metadata.title}")
                if metadata.category:
                    print(f"       Category: {metadata.category}")
                if metadata.author:
                    print(f"       Author: {metadata.author}")
                if metadata.tags:
                    print(f"       Tags: {', '.join(metadata.tags)}")

                # Access raw_content directly - no parsing needed!
                print(f"\n       Content ({len(content.raw_content)} chars):")
                preview = content.raw_content.strip()
                if len(preview) > 100:
                    preview = preview[:97] + "..."
                for line in preview.split("\n"):
                    print(f"       {line}")
                print("=" * 60)

        elif event.type == EventType.BLOCK_REJECTED:
            # Block rejected
            print(f"\n[REJECT] {event.reason}")

    print("\n\nEXTRACTED BLOCKS SUMMARY:")
    print(f"Total blocks: {len(blocks_extracted)}")
    print("\nNotes:")
    for note in blocks_extracted:
        # Type narrow to NoteMetadata for specific access
        if isinstance(note.metadata, NoteMetadata):
            category = f" [{note.metadata.category}]" if note.metadata.category else ""
            author = f" by {note.metadata.author}" if note.metadata.author else ""
            print(f"  - {note.metadata.title}{category}{author}")

    print("\n" + "=" * 60)
    print("KEY POINTS:")
    print("=" * 60)
    print("✓ No custom parse() method needed")
    print("✓ Content stored directly in raw_content field")
    print("✓ Perfect for simple text blocks")
    print("✓ Metadata in YAML frontmatter (rich structure)")
    print("✓ Clean separation: metadata vs. content")
    print("\n✓ DelimiterFrontmatterSyntax processing complete!")


if __name__ == "__main__":
    asyncio.run(main())
