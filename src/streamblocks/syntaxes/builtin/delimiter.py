"""Delimiter-based block syntax implementation.

This syntax handles blocks in the format:
!!block123:type:params
Content goes here
!!block123:end
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from streamblocks.syntaxes.abc import DelimiterSyntax

# Constants
DELIMITER_PARTS_MIN = 2
INLINE_METADATA_PARTS = 3


class DelimiterMetadata(BaseModel):
    """Metadata model for delimiter-based blocks."""

    model_config = ConfigDict(validate_assignment=True)

    hash_id: str = Field(description="Block hash identifier")
    block_type: str = Field(default="block", description="Block type")
    params: str | None = Field(None, description="Optional parameters")
    language: str | None = Field(None, description="Language hint for code blocks")
    attributes: dict[str, str] = Field(default_factory=dict, description="Additional attributes")


class DelimiterContent(BaseModel):
    """Content model for delimiter-based blocks."""

    model_config = ConfigDict(validate_assignment=True)

    text: str = Field(description="The content text")
    is_code: bool = Field(default=False, description="Whether content is code")
    line_count: int = Field(default=0, description="Number of content lines")

    def __init__(self, **data: Any) -> None:
        """Initialize with computed fields."""
        super().__init__(**data)
        if "line_count" not in data and "text" in data:
            self.line_count = len(data["text"].splitlines())


class DelimiterBlockSyntax(DelimiterSyntax[DelimiterMetadata, DelimiterContent]):
    """Delimiter-based block syntax parser.

    Handles blocks like:
    !!block123:shell:bash
    echo "Hello World"
    !!block123:end

    Or simpler forms:
    !!abc123:python
    print("Hello")
    !!abc123:end
    """

    @property
    def name(self) -> str:
        """Syntax identifier."""
        return "delimiter-block"

    @property
    def delimiter_prefix(self) -> str:
        """Prefix for block delimiters."""
        return "!!"

    def detect_line(self, line: str, context: Any = None) -> Any:
        """Enhanced detection for delimiter blocks."""
        from streamblocks.core.models import BlockCandidate
        from streamblocks.core.types import BlockState, DetectionResult

        stripped = line.strip()

        # Check for opening marker
        if context is None:
            if stripped.startswith(self.delimiter_prefix):
                # Extract metadata from opening line
                metadata = self._extract_inline_metadata(stripped)
                if metadata.get("hash_id"):
                    return DetectionResult(is_opening=True, metadata=metadata)
            return DetectionResult()

        # Check for closing marker
        if isinstance(context, BlockCandidate) and context.state == BlockState.ACCUMULATING_CONTENT:
            # Get hash from candidate metadata
            hash_id = context.metadata.get("hash_id", "")
            if hash_id:
                expected_closing = f"{self.delimiter_prefix}{hash_id}{self.end_suffix}"
                if stripped == expected_closing:
                    return DetectionResult(is_closing=True)

        return DetectionResult()

    def _extract_inline_metadata(self, opening_line: str) -> dict[str, str]:
        """Extract metadata from opening delimiter line."""
        # Remove prefix
        line = opening_line.strip()
        if line.startswith(self.delimiter_prefix):
            line = line[len(self.delimiter_prefix):]

        # Split by colon
        parts = line.split(":")
        metadata: dict[str, str] = {}

        if len(parts) >= 1:
            # First part is always the hash ID
            metadata["hash_id"] = parts[0]

        if len(parts) >= DELIMITER_PARTS_MIN:
            # Second part is the block type
            metadata["block_type"] = parts[1]

        if len(parts) >= INLINE_METADATA_PARTS:
            # Third part and beyond are parameters
            metadata["params"] = ":".join(parts[2:])

            # Special handling for common patterns
            if metadata["block_type"] in ["code", "shell", "python", "javascript"]:
                # For code blocks, params often indicate language
                metadata["language"] = parts[2] if len(parts) > 2 else metadata["block_type"]

        return metadata

    def parse_metadata_dict(self, metadata_dict: dict[str, str]) -> DelimiterMetadata:
        """Convert metadata dictionary to typed metadata model."""
        # Required field
        hash_id = metadata_dict.get("hash_id", "")
        if not hash_id:
            raise ValueError("Missing required hash_id in metadata")

        # Build metadata object
        return DelimiterMetadata(
            hash_id=hash_id,
            block_type=metadata_dict.get("block_type", "block"),
            params=metadata_dict.get("params"),
            language=metadata_dict.get("language"),
            attributes={k: v for k, v in metadata_dict.items()
                       if k not in ["hash_id", "block_type", "params", "language"]}
        )

    def parse_content(self, content_text: str) -> DelimiterContent:
        """Parse content text into content model."""
        # Detect if content looks like code
        is_code = False

        if content_text.strip():
            # Simple heuristics for code detection
            lines = content_text.splitlines()
            code_indicators = [
                any("import " in line or "from " in line for line in lines[:10]),
                any("function " in line or "def " in line for line in lines[:10]),
                any(line.strip().endswith(";") for line in lines[:10]),
                any(line.strip().endswith("{") for line in lines[:10]),
            ]
            is_code = any(code_indicators)

        return DelimiterContent(
            text=content_text,
            is_code=is_code
        )

    def get_block_type_hints(self) -> list[str]:
        """Get list of block types this syntax typically produces."""
        return ["block", "code", "shell", "output", "data"]

    def supports_nested_blocks(self) -> bool:
        """Delimiter blocks can support nesting with different hash IDs."""
        return True

    def validate_block(self, metadata: DelimiterMetadata, content: DelimiterContent) -> bool:
        """Validate parsed block."""
        # Must have a hash ID
        if not metadata.hash_id:
            return False

        # Hash ID should be alphanumeric (with optional dashes/underscores)
        return bool(re.match("^[a-zA-Z0-9_-]+$", metadata.hash_id))
