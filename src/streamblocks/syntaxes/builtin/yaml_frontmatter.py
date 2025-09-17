"""Delimiter frontmatter syntax implementation.

This syntax handles blocks in the format:
!!start
---
metadata: here
---
content
!!end
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import yaml

from streamblocks.core.types import DetectionResult
from streamblocks.syntaxes.abc import FrontmatterSyntax

if TYPE_CHECKING:
    from pydantic import BaseModel


# Constants
FRONTMATTER_DELIMITER = "---"


class DelimiterFrontmatterSyntax[TMetadata: BaseModel, TContent: BaseModel](
    FrontmatterSyntax[TMetadata, TContent]
):
    """Delimiter frontmatter syntax parser.

    This is a generic syntax parser for delimiter-based blocks with YAML frontmatter.
    Users must provide their own metadata and content model classes.

    Format:
    !!start
    ---
    key: value
    ---
    content
    !!end

    Example usage:
    ```python
    class MyMetadata(BaseModel):
        id: str
        type: str
        name: str | None = None

    class MyContent(BaseModel):
        text: str

    syntax = DelimiterFrontmatterSyntax(
        metadata_class=MyMetadata,
        content_class=MyContent,
        start_delimiter="!!start",
        end_delimiter="!!end"
    )
    ```
    """

    def __init__(
        self,
        metadata_class: type[TMetadata],
        content_class: type[TContent],
        start_delimiter: str = "!!start",
        end_delimiter: str = "!!end",
    ) -> None:
        """Initialize with user-provided model classes.

        Args:
            metadata_class: Pydantic model class for metadata
            content_class: Pydantic model class for content
            start_delimiter: Start delimiter (default: "!!start")
            end_delimiter: End delimiter (default: "!!end")
        """
        self.metadata_class = metadata_class
        self.content_class = content_class
        self._start_delimiter = start_delimiter
        self._end_delimiter = end_delimiter
        self._frontmatter_pattern = re.compile(rf"^{re.escape(FRONTMATTER_DELIMITER)}\s*$")

    @property
    def name(self) -> str:
        """Syntax identifier."""
        return f"delimiter_frontmatter_{self._start_delimiter}"

    @property
    def frontmatter_delimiter(self) -> str:
        """Get frontmatter delimiter."""
        return FRONTMATTER_DELIMITER

    def detect_line(self, line: str, context: Any = None) -> DetectionResult:
        """Detect delimiter markers and frontmatter boundaries."""
        from streamblocks.core.models import BlockCandidate

        stripped = line.strip()

        if context is None:
            # Looking for opening
            if stripped == self._start_delimiter:
                return DetectionResult(is_opening=True)
        # Inside a block
        elif isinstance(context, BlockCandidate):
            if context.state.value == "header_detected":
                # After !!start, check for frontmatter start
                if self._is_frontmatter_boundary(line):
                    return DetectionResult(is_metadata_boundary=True)
                # No frontmatter, move directly to content
                return DetectionResult()
            if context.state.value == "accumulating_metadata":
                # Check for metadata end
                if self._is_frontmatter_boundary(line):
                    return DetectionResult(is_metadata_boundary=True)
            elif context.state.value == "accumulating_content" and stripped == self._end_delimiter:
                return DetectionResult(is_closing=True)

        return DetectionResult()

    def _is_frontmatter_boundary(self, line: str) -> bool:
        """Check if line is a frontmatter boundary (---)."""
        return self._frontmatter_pattern.match(line.strip()) is not None

    def should_accumulate_metadata(self, candidate: Any) -> bool:
        """Check if we should accumulate metadata lines."""
        from streamblocks.core.models import BlockCandidate

        if isinstance(candidate, BlockCandidate):
            # We accumulate metadata between the --- delimiters
            return candidate.state.value in ["header_detected", "accumulating_metadata"]
        return False

    def parse_metadata(self, yaml_text: str) -> TMetadata:
        """Parse YAML metadata into user's metadata model."""
        if not yaml_text.strip():
            # Try to create empty metadata
            return self.metadata_class()

        try:
            data = yaml.safe_load(yaml_text)
            if data is None:
                return self.metadata_class()
            if not isinstance(data, dict):
                # If user's metadata model can handle non-dict data, let it try
                return self.metadata_class(data)  # type: ignore[call-arg]
            return self.metadata_class(**data)
        except yaml.YAMLError as e:
            # Let user's model handle invalid data or raise
            raise ValueError(f"Invalid YAML metadata: {e}") from e

    def parse_content(self, content_text: str) -> TContent:
        """Parse content into user's content model."""
        # Try different initialization strategies
        if hasattr(self.content_class, "parse"):
            # If content class has a parse method, use it
            return self.content_class.parse(content_text)  # type: ignore[attr-defined, no-any-return]

        # Try common field names
        init_kwargs: dict[str, Any] = {}
        if hasattr(self.content_class, "model_fields"):
            fields = self.content_class.model_fields
            # Try common content field names
            for field_name in ["text", "content", "raw", "body", "data"]:
                if field_name in fields:
                    init_kwargs[field_name] = content_text
                    break

        if not init_kwargs:
            # Fallback: try to initialize with positional argument
            try:
                return self.content_class(content_text)  # type: ignore[call-arg]
            except Exception:
                # Last resort: provide with common field name
                init_kwargs = {"text": content_text}

        return self.content_class(**init_kwargs)

    def get_opening_pattern(self) -> str | None:
        """Pattern for opening delimiter."""
        return rf"^{re.escape(self._start_delimiter)}$"

    def get_closing_pattern(self) -> str | None:
        """Pattern for closing delimiter."""
        return rf"^{re.escape(self._end_delimiter)}$"

    def get_block_type_hints(self) -> list[str]:
        """Get list of block types this syntax typically produces."""
        return ["delimiter", "frontmatter", "document"]

    def validate_block(self, metadata: TMetadata, content: TContent) -> bool:
        """Validate parsed block."""
        # Delegate validation to user's models
        return True
