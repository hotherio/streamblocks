"""Markdown frontmatter syntax implementation.

This syntax handles blocks in the format:
```[info]
---
metadata: here
---
content
```
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
BACKTICK_COUNT = 3


class MarkdownFrontmatterSyntax[TMetadata: BaseModel, TContent: BaseModel](
    FrontmatterSyntax[TMetadata, TContent]
):
    """Markdown frontmatter syntax parser.

    This is a generic syntax parser for markdown fence blocks with YAML frontmatter.
    Users must provide their own metadata and content model classes.

    Format:
    ```[info_string]
    ---
    key: value
    ---
    content
    ```

    Example usage:
    ```python
    class MyMetadata(BaseModel):
        id: str
        type: str
        title: str | None = None

    class MyContent(BaseModel):
        text: str
        format: str = "markdown"

    syntax = MarkdownFrontmatterSyntax(
        metadata_class=MyMetadata,
        content_class=MyContent,
        fence="```",
        info_string=None
    )
    ```
    """

    def __init__(
        self,
        metadata_class: type[TMetadata],
        content_class: type[TContent],
        fence: str = "```",
        info_string: str | None = None,
    ) -> None:
        """Initialize with user-provided model classes.

        Args:
            metadata_class: Pydantic model class for metadata
            content_class: Pydantic model class for content
            fence: Fence marker (default: "```")
            info_string: Optional info string to match after fence
        """
        self.metadata_class = metadata_class
        self.content_class = content_class
        self._fence = fence
        self._info_string = info_string
        self._fence_pattern = self._build_fence_pattern()
        self._frontmatter_pattern = re.compile(r"^---\s*$")

    def _build_fence_pattern(self) -> re.Pattern[str]:
        """Build regex pattern for fence detection."""
        pattern_str = rf"^{re.escape(self._fence)}"
        if self._info_string:
            pattern_str += re.escape(self._info_string)
        return re.compile(pattern_str)

    @property
    def name(self) -> str:
        """Syntax identifier."""
        suffix = f"_{self._info_string}" if self._info_string else ""
        return f"markdown_frontmatter{suffix}"

    @property
    def frontmatter_delimiter(self) -> str:
        """Get frontmatter delimiter."""
        return "---"

    def detect_line(self, line: str, context: Any = None) -> DetectionResult:
        """Detect markdown fence markers and frontmatter boundaries."""
        from streamblocks.core.models import BlockCandidate

        if context is None:
            # Looking for opening fence
            if self._fence_pattern.match(line.strip()):
                return DetectionResult(is_opening=True)
        # Inside a block
        elif isinstance(context, BlockCandidate):
            if context.state.value == "accumulating_metadata":
                # Check for metadata section boundaries
                if self._is_frontmatter_boundary(line):
                    if not context.metadata_lines:
                        # First --- marks start of metadata
                        return DetectionResult(is_metadata_boundary=True)
                    # Second --- marks end of metadata
                    return DetectionResult(is_metadata_boundary=True)
            elif context.state.value == "accumulating_content" and line.strip() == self._fence:
                return DetectionResult(is_closing=True)

        return DetectionResult()

    def _is_frontmatter_boundary(self, line: str) -> bool:
        """Check if line is a frontmatter boundary (---)."""
        return self._frontmatter_pattern.match(line.strip()) is not None

    def should_accumulate_metadata(self, candidate: Any) -> bool:
        """Check if we should accumulate metadata lines."""
        from streamblocks.core.models import BlockCandidate

        if isinstance(candidate, BlockCandidate):
            # We accumulate metadata after the opening fence until we hit the second ---
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
                # Last resort: empty initialization
                init_kwargs = {"text": content_text}

        return self.content_class(**init_kwargs)

    def get_opening_pattern(self) -> str | None:
        """Pattern for opening fence."""
        return rf"^{re.escape(self._fence)}.*$"

    def get_closing_pattern(self) -> str | None:
        """Pattern for closing fence."""
        return rf"^{re.escape(self._fence)}\s*$"

    def get_block_type_hints(self) -> list[str]:
        """Get list of block types this syntax typically produces."""
        return ["markdown", "document", "frontmatter"]

    def validate_block(self, metadata: TMetadata, content: TContent) -> bool:
        """Validate parsed block."""
        # Delegate validation to user's models
        return True
