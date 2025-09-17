"""Mock syntax implementation for testing.

This module provides a simple mock syntax parser that can be
used for testing the syntax framework.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from streamblocks.core.types import (
    BlockState,
    DetectionResult,
)
from streamblocks.syntaxes.abc import DelimiterSyntax

if TYPE_CHECKING:
    from streamblocks.core.models import BlockCandidate

# Constants
MIN_PARTS_FOR_TYPE = 2


class MockMetadata(BaseModel):
    """Mock metadata model."""

    block_id: str
    block_type: str = "mock"
    params: dict[str, str] = Field(default_factory=dict)


class MockContent(BaseModel):
    """Mock content model."""

    text: str
    lines: list[str] = Field(default_factory=list)


class MockSyntax(DelimiterSyntax[MockMetadata, MockContent]):
    """Mock syntax parser for testing.

    Uses simple delimiter format:
    - Opening: !!mock:id:params
    - Content: any text
    - Closing: !!mock:end
    """

    @property
    def name(self) -> str:
        """Syntax name."""
        return "mock"

    @property
    def delimiter_prefix(self) -> str:
        """Delimiter prefix."""
        return "!!"

    def _extract_inline_metadata(self, opening_line: str) -> dict[str, str]:
        """Extract metadata from opening line.

        Format: !!mock:id[:key=value,...]
        """
        # Remove prefix
        line = opening_line.strip()
        if line.startswith("!!"):
            line = line[2:]  # Remove the !! prefix
        parts = line.split(":")

        metadata: dict[str, str] = {}
        if len(parts) >= 1:
            metadata["block_id"] = parts[0]

        # Parse optional parameters
        if len(parts) >= MIN_PARTS_FOR_TYPE:
            # Join remaining parts in case values contain colons
            param_str = ":".join(parts[1:])
            if param_str and param_str != "end":
                # Parse key=value pairs
                for pair in param_str.split(","):
                    if "=" in pair:
                        key, value = pair.split("=", 1)
                        metadata[key.strip()] = value.strip()

        return metadata

    def parse_metadata_dict(self, metadata_dict: dict[str, str]) -> MockMetadata:
        """Convert metadata dict to model."""
        # Extract known fields
        block_id = metadata_dict.get("block_id", "unknown")

        # Everything else goes in params
        params = {k: v for k, v in metadata_dict.items() if k != "block_id"}

        return MockMetadata(block_id=block_id, params=params)

    def parse_content(self, content_text: str) -> MockContent:
        """Parse content text."""
        lines = content_text.split("\n") if content_text else []
        return MockContent(text=content_text, lines=lines)

    def detect_line(self, line: str, context: BlockCandidate | None = None) -> DetectionResult:
        """Detect mock syntax markers."""
        stripped = line.strip()

        # Opening detection
        if context is None:
            if stripped.startswith("!!mock:"):
                # Extract metadata
                metadata = self._extract_inline_metadata(stripped)
                return DetectionResult(is_opening=True, metadata=metadata)
            return DetectionResult()

        # Closing detection
        if context and context.state == BlockState.ACCUMULATING_CONTENT:
            # Get the block ID from the opening metadata
            block_id = context.metadata_lines[0] if context.metadata_lines else "mock"
            if ":" in block_id:
                block_id = block_id.split(":")[0].lstrip("!")
            expected_closing = f"!!{block_id}:end"

            if stripped == expected_closing:
                return DetectionResult(is_closing=True)

        return DetectionResult()

    def get_block_type_hints(self) -> list[str]:
        """Return block types this syntax handles."""
        return ["mock", "test"]
