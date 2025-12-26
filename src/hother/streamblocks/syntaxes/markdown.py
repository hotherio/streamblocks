"""Markdown-based syntax implementations."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from hother.streamblocks.core.models import extract_block_types
from hother.streamblocks.core.types import BaseContent, BaseMetadata, DetectionResult, ParseResult
from hother.streamblocks.syntaxes.base import BaseSyntax, YAMLFrontmatterMixin

if TYPE_CHECKING:
    from hother.streamblocks.core.models import BlockCandidate, ExtractedBlock


class MarkdownFrontmatterSyntax(BaseSyntax, YAMLFrontmatterMixin):
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
        fence: str = "```",
        info_string: str | None = None,
    ) -> None:
        """Initialize markdown frontmatter syntax.

        Args:
            fence: Fence string (e.g., "```")
            info_string: Optional info string after fence
        """
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

    def extract_block_type(self, candidate: BlockCandidate) -> str | None:
        """Extract block_type from YAML frontmatter."""
        if not candidate.metadata_lines:
            # Try to infer from info string
            return self.info_string

        # Parse YAML to extract block_type
        metadata_dict = self._parse_yaml_metadata(candidate.metadata_lines)
        if metadata_dict and "block_type" in metadata_dict:
            return str(metadata_dict["block_type"])
        # No block_type found in metadata or parse failed, return info_string
        return self.info_string

    def _set_metadata_defaults(
        self,
        metadata_dict: dict[str, Any],
        candidate: BlockCandidate,
        metadata_class: type[BaseMetadata],
    ) -> None:
        """Set default values for id and block_type if using BaseMetadata."""
        if metadata_class is not BaseMetadata:
            return

        if "id" not in metadata_dict:
            metadata_dict["id"] = f"block_{candidate.compute_hash()}"

        if "block_type" not in metadata_dict:
            metadata_dict["block_type"] = self.info_string or "markdown"

    def _parse_metadata_instance(
        self,
        metadata_class: type[BaseMetadata],
        metadata_dict: dict[str, Any],
    ) -> ParseResult[BaseMetadata, BaseContent] | BaseMetadata:
        """Parse and validate metadata dict into metadata instance."""
        try:
            return metadata_class(**metadata_dict)
        except ValidationError as e:
            return ParseResult(success=False, error=f"Metadata validation error: {e}", exception=e)
        except (TypeError, ValueError, KeyError) as e:
            return ParseResult(success=False, error=f"Invalid metadata: {e}", exception=e)

    def _parse_content_instance(
        self,
        content_class: type[BaseContent],
        candidate: BlockCandidate,
    ) -> ParseResult[BaseMetadata, BaseContent] | BaseContent:
        """Parse content lines into content instance."""
        content_text = "\n".join(candidate.content_lines)

        try:
            return content_class.parse(content_text)
        except ValidationError as e:
            return ParseResult(success=False, error=f"Content validation error: {e}", exception=e)
        except (TypeError, ValueError, KeyError) as e:
            return ParseResult(success=False, error=f"Invalid content: {e}", exception=e)

    def parse_block(
        self, candidate: BlockCandidate, block_class: type[Any] | None = None
    ) -> ParseResult[BaseMetadata, BaseContent]:
        """Parse the complete block using the specified block class."""

        # Extract metadata and content classes
        if block_class is None:
            metadata_class = BaseMetadata
            content_class = BaseContent
        else:
            metadata_class, content_class = extract_block_types(block_class)

        # Parse YAML metadata
        metadata_dict, yaml_error = self._parse_yaml_metadata_strict(candidate.metadata_lines)
        if yaml_error:
            return ParseResult(success=False, error=f"YAML parse error: {yaml_error}", exception=yaml_error)

        # Set defaults for BaseMetadata
        self._set_metadata_defaults(metadata_dict, candidate, metadata_class)

        # Parse metadata instance
        metadata_result = self._parse_metadata_instance(metadata_class, metadata_dict)
        if isinstance(metadata_result, ParseResult):
            return metadata_result

        # Parse content instance
        content_result = self._parse_content_instance(content_class, candidate)
        if isinstance(content_result, ParseResult):
            return content_result

        return ParseResult(success=True, metadata=metadata_result, content=content_result)

    def validate_block(self, _block: ExtractedBlock[BaseMetadata, BaseContent]) -> bool:
        """Additional validation after parsing."""
        return True
