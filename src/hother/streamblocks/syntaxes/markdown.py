"""Markdown-based syntax implementations."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, cast

import yaml
from pydantic import BaseModel

from hother.streamblocks.core.models import BaseContent, BaseMetadata
from hother.streamblocks.core.types import DetectionResult, ParseResult

if TYPE_CHECKING:
    from hother.streamblocks.core.models import BlockCandidate


class MarkdownFrontmatterSyntax[TMetadata: BaseModel, TContent: BaseModel]:
    """Syntax: Markdown-style with YAML frontmatter.

    Format:
    ```[info]
    ---
    key: value
    ---
    content
    ```
    """

    def __init__(
        self,
        name: str,
        metadata_class: type[TMetadata] | None = None,
        content_class: type[TContent] | None = None,
        fence: str = "```",
        info_string: str | None = None,
    ) -> None:
        """Initialize markdown frontmatter syntax.

        Args:
            name: Unique name for this syntax instance
            metadata_class: Class for parsing metadata (defaults to BaseMetadata)
            content_class: Class for parsing content (defaults to BaseContent)
            fence: Fence string (e.g., "```")
            info_string: Optional info string after fence
        """
        self._name = name
        self.metadata_class = metadata_class or BaseMetadata
        self.content_class = content_class or BaseContent
        self.fence = fence
        self.info_string = info_string
        self._fence_pattern = self._build_fence_pattern()
        self._frontmatter_pattern = re.compile(r"^---\s*$")

    def _build_fence_pattern(self) -> re.Pattern[str]:
        """Build pattern for fence detection."""
        pattern_str = rf"^{re.escape(self.fence)}"
        if self.info_string:
            pattern_str += re.escape(self.info_string)
        return re.compile(pattern_str)

    @property
    def name(self) -> str:
        """Get syntax name."""
        return self._name

    def detect_line(self, line: str, candidate: BlockCandidate | None = None) -> DetectionResult:
        """Detect markdown fence markers and frontmatter boundaries."""
        if candidate is None:
            # Looking for opening fence
            if self._fence_pattern.match(line):
                return DetectionResult(is_opening=True)
        # Inside a block
        elif candidate.current_section == "header":
            # Check if this is frontmatter start
            if self._frontmatter_pattern.match(line):
                candidate.current_section = "metadata"
                return DetectionResult(is_metadata_boundary=True)
            # Skip empty lines in header - frontmatter might follow
            if line.strip() == "":
                return DetectionResult()
            # Non-empty, non-frontmatter line - move to content
            candidate.current_section = "content"
            candidate.content_lines.append(line)
        elif candidate.current_section == "metadata":
            # Check for metadata end
            if self._frontmatter_pattern.match(line):
                candidate.current_section = "content"
                return DetectionResult(is_metadata_boundary=True)
            candidate.metadata_lines.append(line)
        elif candidate.current_section == "content":
            # Check for closing fence
            if line.strip() == self.fence:
                return DetectionResult(is_closing=True)
            candidate.content_lines.append(line)

        return DetectionResult()

    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        """Check if we're still in metadata section."""
        return candidate.current_section in ["header", "metadata"]

    def parse_block(self, candidate: BlockCandidate) -> ParseResult[TMetadata, TContent]:
        """Parse the complete block."""
        # Parse metadata from accumulated metadata lines
        metadata_dict: dict[str, Any] = {}
        if candidate.metadata_lines:
            yaml_content = "\n".join(candidate.metadata_lines)
            try:
                metadata_dict = yaml.safe_load(yaml_content) or {}
            except Exception as e:
                return ParseResult(success=False, error=f"Invalid YAML: {e}")

        # Ensure id and block_type have defaults
        # Only fill in defaults if using BaseMetadata (no custom class provided)
        if self.metadata_class is BaseMetadata:
            if "id" not in metadata_dict:
                # Generate an ID based on hash of content
                metadata_dict["id"] = f"block_{candidate.compute_hash()}"
            if "block_type" not in metadata_dict:
                # Try to infer from info string or use default
                if self.info_string:
                    metadata_dict["block_type"] = self.info_string
                else:
                    metadata_dict["block_type"] = "markdown"

        try:
            # Convert all metadata values to proper types for type safety
            typed_metadata = {k: str(v) if not isinstance(v, str) else v for k, v in metadata_dict.items()}
            metadata = self.metadata_class(**typed_metadata)
        except Exception as e:
            return ParseResult(success=False, error=f"Invalid metadata: {e}")

        # Parse content
        content_text = "\n".join(candidate.content_lines)

        try:
            # All content classes must have parse method
            content = cast("TContent", self.content_class.parse(content_text))  # type: ignore[attr-defined]
        except Exception as e:
            return ParseResult(success=False, error=f"Invalid content: {e}")

        return ParseResult(success=True, metadata=metadata, content=content)

    def validate_block(self, metadata: TMetadata, content: TContent) -> bool:
        """Additional validation after parsing."""
        return True
