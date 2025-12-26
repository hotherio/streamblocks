#!/usr/bin/env python3
"""Creating a completely custom syntax format."""

# --8<-- [start:imports]
import asyncio
import re
from textwrap import dedent
from typing import Any

from hother.streamblocks import Registry, StreamBlockProcessor
from hother.streamblocks.core.models import BlockCandidate, extract_block_types
from hother.streamblocks.core.types import (
    BaseContent,
    BaseMetadata,
    BlockEndEvent,
    DetectionResult,
    ParseResult,
)
from hother.streamblocks.syntaxes.base import BaseSyntax
from hother.streamblocks_examples.blocks.agent.files import FileOperations

# --8<-- [end:imports]


# --8<-- [start:custom_syntax]
class XMLBlockSyntax(BaseSyntax):
    """Custom XML-like syntax for blocks.

    Format:
        <!-- block:type id="..." key="value" -->
        content here
        <!-- /block -->
    """

    def __init__(self) -> None:
        """Initialize XML block syntax."""
        # Pattern: <!-- block:type attr="value" ... -->
        self._opening_pattern = re.compile(r"^<!--\s*block:(\w+)\s+(.+?)\s*-->$")
        # Pattern: <!-- /block -->
        self._closing_pattern = re.compile(r"^<!--\s*/block\s*-->$")
        # Pattern for attributes: key="value"
        self._attr_pattern = re.compile(r'(\w+)="([^"]*)"')

    def detect_line(self, line: str, candidate: BlockCandidate | None) -> DetectionResult:
        """Detect XML-style block markers."""
        stripped = line.strip()

        if candidate is None:
            # Looking for opening tag
            match = self._opening_pattern.match(stripped)
            if match:
                block_type = match.group(1)
                attrs_str = match.group(2)

                # Parse attributes
                attrs = dict(self._attr_pattern.findall(attrs_str))
                attrs["block_type"] = block_type

                return DetectionResult(is_opening=True, metadata=attrs)
        else:
            # Inside a block - check for closing
            if self._closing_pattern.match(stripped):
                return DetectionResult(is_closing=True)
            # Accumulate content
            candidate.content_lines.append(line)

        return DetectionResult()

    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        """No separate metadata section - all in opening tag."""
        return False

    def extract_block_type(self, candidate: BlockCandidate) -> str | None:
        """Extract block_type from cached metadata."""
        if not candidate.lines:
            return None

        match = self._opening_pattern.match(candidate.lines[0].strip())
        return match.group(1) if match else None

    def parse_block(
        self, candidate: BlockCandidate, block_class: type[Any] | None = None
    ) -> ParseResult[BaseMetadata, BaseContent]:
        """Parse the complete block."""
        if block_class is None:
            metadata_class = BaseMetadata
            content_class = BaseContent
        else:
            metadata_class, content_class = extract_block_types(block_class)

        # Parse opening line for metadata
        if not candidate.lines:
            return ParseResult(success=False, error="No lines in candidate")

        match = self._opening_pattern.match(candidate.lines[0].strip())
        if not match:
            return ParseResult(success=False, error="Invalid opening tag")

        block_type = match.group(1)
        attrs_str = match.group(2)
        metadata_dict: dict[str, Any] = dict(self._attr_pattern.findall(attrs_str))
        metadata_dict["block_type"] = block_type

        try:
            metadata = metadata_class(**metadata_dict)
        except Exception as e:
            return ParseResult(success=False, error=f"Metadata error: {e}", exception=e)

        # Content is accumulated lines (excluding opening/closing)
        content_text = "\n".join(candidate.content_lines)

        try:
            content = content_class.parse(content_text)
        except Exception as e:
            return ParseResult(success=False, error=f"Content error: {e}", exception=e)

        return ParseResult(success=True, metadata=metadata, content=content)


# --8<-- [end:custom_syntax]


# --8<-- [start:main]
async def main() -> None:
    """Demonstrate custom XML-like syntax."""
    # --8<-- [start:setup]
    syntax = XMLBlockSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry)
    # --8<-- [end:setup]

    # --8<-- [start:stream]
    text = dedent("""
        Some text before the block.

        <!-- block:files_operations id="ops001" description="Create files" -->
        src/main.py:C
        src/utils.py:E
        <!-- /block -->

        Some text after the block.
    """).strip()

    from hother.streamblocks_examples.helpers.simulator import simple_text_stream

    # --8<-- [end:stream]

    # --8<-- [start:process]
    print("=== Custom XML-like Syntax ===")
    async for event in processor.process_stream(simple_text_stream(text)):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block:
                print("Extracted block:")
                print(block.model_dump_json(indent=2))
    # --8<-- [end:process]


# --8<-- [end:main]


if __name__ == "__main__":
    asyncio.run(main())
