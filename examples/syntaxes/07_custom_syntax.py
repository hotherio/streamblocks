"""Example demonstrating how to create a custom syntax.

This advanced example shows how to extend BaseSyntax to create your own
custom block format. Perfect for domain-specific formats or integrating
with existing structured text formats.
"""

import asyncio
import re
from collections.abc import AsyncIterator
from typing import Any, Literal

from pydantic import Field

import hother.streamblocks as sb
from hother.streamblocks.core.models import Block, BlockCandidate, extract_block_types
from hother.streamblocks.core.types import BaseContent, BaseMetadata, DetectionResult, ParseResult
from hother.streamblocks.syntaxes.base import BaseSyntax


# =============================================================================
# Custom Syntax: XML-Style Blocks
# =============================================================================


class XmlStyleSyntax(BaseSyntax):
    """Custom syntax using XML-style tags.

    Format:
        <block id="example" type="note">
        Content goes here
        </block>
    """

    def __init__(self) -> None:
        """Initialize XML-style syntax."""
        # Opening tag: <block id="..." type="...">
        self._opening_pattern = re.compile(r'<block\s+id="([^"]+)"\s+type="([^"]+)">')
        # Closing tag: </block>
        self._closing_pattern = re.compile(r"</block>")

    def detect_line(self, line: str, candidate: BlockCandidate | None = None) -> DetectionResult:
        """Detect XML-style block markers."""
        if candidate is None:
            # Looking for opening tag
            match = self._opening_pattern.search(line)
            if match:
                block_id, block_type = match.groups()
                return DetectionResult(
                    is_opening=True,
                    metadata={
                        "id": block_id,
                        "block_type": block_type,
                    },
                )
        else:
            # Inside a block - check for closing tag
            if self._closing_pattern.search(line):
                return DetectionResult(is_closing=True)

            # Accumulate content
            candidate.content_lines.append(line)

        return DetectionResult()

    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        """No separate metadata section - it's in the opening tag."""
        return False

    def extract_block_type(self, candidate: BlockCandidate) -> str | None:
        """Extract block type from opening tag."""
        if not candidate.lines:
            return None

        match = self._opening_pattern.search(candidate.lines[0])
        if match:
            return match.group(2)  # type is the second group

        return None

    def parse_block(
        self, candidate: BlockCandidate, block_class: type[Any] | None = None
    ) -> ParseResult[BaseMetadata, BaseContent]:
        """Parse the XML-style block."""
        # Extract metadata and content classes
        if block_class is None:
            metadata_class = BaseMetadata
            content_class = BaseContent
        else:
            metadata_class, content_class = extract_block_types(block_class)

        # Extract metadata from opening tag
        if not candidate.lines:
            return ParseResult(success=False, error="Empty block")

        match = self._opening_pattern.search(candidate.lines[0])
        if not match:
            return ParseResult(success=False, error="Invalid opening tag")

        block_id, block_type = match.groups()

        try:
            metadata = metadata_class(id=block_id, block_type=block_type)
        except Exception as e:
            return ParseResult(success=False, error=f"Invalid metadata: {e}", exception=e)

        # Parse content
        content_text = "\n".join(candidate.content_lines)

        try:
            content = content_class.parse(content_text)
        except Exception as e:
            return ParseResult(success=False, error=f"Invalid content: {e}", exception=e)

        return ParseResult(success=True, metadata=metadata, content=content)

    def serialize_block(self, block: Any) -> str:
        """Serialize block to XML-style format."""
        metadata = block.metadata
        content = block.content.raw_content

        opening = f'<block id="{metadata.id}" type="{metadata.block_type}">'
        closing = "</block>"

        return f"{opening}\n{content}\n{closing}"

    def describe_format(self) -> str:
        """Describe XML-style format."""
        return """XML-Style Syntax

Format:
<block id="example" type="note">
content lines
</block>

Components:
- Opening tag: <block id="..." type="...">
- Content: Any text content
- Closing tag: </block>"""

    def validate_block(self, _block: sb.ExtractedBlock[BaseMetadata, BaseContent]) -> bool:
        """Additional validation."""
        return True


# =============================================================================
# Define Block Types
# =============================================================================


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
# Example Stream
# =============================================================================


async def example_stream() -> AsyncIterator[str]:
    """Example stream with XML-style blocks."""
    text = """
Here's a document with custom XML-style blocks.

<block id="note01" type="note">
This is a note using our custom XML-style syntax!
It's easy to read and parse.
</block>

Some text between blocks.

<block id="note02" type="note">
Another note with custom syntax.
You can create any format you want by extending BaseSyntax.
</block>

More text here.

<block id="note03" type="note">
The possibilities are endless!
</block>

That's all!
"""

    # Simulate streaming
    chunk_size = 50
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        yield chunk
        await asyncio.sleep(0.01)


# =============================================================================
# Main
# =============================================================================


async def main() -> None:
    """Main example function."""
    print("=== Custom Syntax Example ===\n")
    print("This example demonstrates creating a custom XML-style syntax")
    print("by extending the BaseSyntax class.\n")

    # Create our custom syntax
    custom_syntax = XmlStyleSyntax()

    # Create registry with custom syntax
    registry = sb.Registry(syntax=custom_syntax)
    registry.register("note", NoteBlock)

    # Create processor
    processor = sb.StreamBlockProcessor(registry)

    # Process stream
    print("Processing XML-style blocks...\n")

    blocks_extracted: list[sb.ExtractedBlock[BaseMetadata, BaseContent]] = []

    async for event in processor.process_stream(example_stream()):
        if event.type == sb.EventType.RAW_TEXT:
            if event.data.strip():
                text = event.data.strip()
                if len(text) > 60:
                    text = text[:57] + "..."
                print(f"[TEXT] {text}")

        elif event.type == sb.EventType.BLOCK_EXTRACTED:
            block = event.block
            blocks_extracted.append(block)

            if isinstance(block.metadata, NoteMetadata) and isinstance(block.content, NoteContent):
                print(f"\n{'=' * 60}")
                print(f"[NOTE] {block.metadata.id}")
                print(f"       {block.content.text}")
                print("=" * 60)

    print(f"\n\nTotal blocks extracted: {len(blocks_extracted)}")

    # Show format example
    print("\n" + "=" * 60)
    print("CUSTOM SYNTAX FORMAT")
    print("=" * 60)
    print(custom_syntax.describe_format())

    print("\n" + "=" * 60)
    print("HOW TO CREATE CUSTOM SYNTAX")
    print("=" * 60)
    print("\n1. Extend BaseSyntax class")
    print("   class MySyntax(BaseSyntax):")
    print("       ...")
    print("\n2. Implement required methods:")
    print("   - detect_line(): Detect opening/closing markers")
    print("   - should_accumulate_metadata(): Return True if in metadata section")
    print("   - extract_block_type(): Extract block type for registry lookup")
    print("   - parse_block(): Parse complete block")
    print("   - serialize_block(): Convert block back to text")
    print("   - describe_format(): Describe your format")
    print("   - validate_block(): Optional additional validation")
    print("\n3. Use your custom syntax:")
    print("   syntax = MySyntax()")
    print("   registry = Registry(syntax=syntax)")
    print("   processor = StreamBlockProcessor(registry)")

    print("\n✓ Custom syntax processing complete!")


if __name__ == "__main__":
    asyncio.run(main())
