"""Delimiter-based syntax implementations."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from hother.streamblocks.core.models import extract_block_types
from hother.streamblocks.core.types import BaseContent, BaseMetadata, DetectionResult, ParseResult, SectionType
from hother.streamblocks.syntaxes.base import BaseSyntax, YAMLFrontmatterMixin

if TYPE_CHECKING:
    from hother.streamblocks.core.models import BlockCandidate, ExtractedBlock

# Minimum lines required for a block (header + closing delimiter)
_MIN_BLOCK_LINES = 2


@runtime_checkable
class ContentParser(Protocol):
    """Protocol for content classes with a parse method."""

    @classmethod
    def parse(cls, raw_text: str) -> BaseContent:
        """Parse raw text into content."""
        ...


class DelimiterPreambleSyntax(BaseSyntax):
    """Syntax: !! delimiter with inline metadata.

    This syntax uses delimiter markers with inline metadata in the opening line.
    Metadata is extracted from the delimiter preamble, and all lines between
    opening and closing delimiters become the content.

    Format:
        !!<id>:<type>[:param1:param2:...]
        Content lines here
        !!end

    The opening delimiter must include:
        - Block ID (alphanumeric, required)
        - Block type (alphanumeric, required)
        - Additional parameters (optional, colon-separated)

    Additional parameters are stored as param_0, param_1, etc. in metadata.

    Examples:
        >>> # Simple block with just ID and type
        >>> '''
        ... !!patch001:patch
        ... Fix the login bug
        ... !!end
        ... '''
        >>>
        >>> # Block with parameters
        >>> '''
        ... !!file123:operation:create:urgent
        ... Create new config file
        ... !!end
        ... '''
        >>> # Metadata will be: {
        >>> #     "id": "file123",
        >>> #     "block_type": "operation",
        >>> #     "param_0": "create",
        >>> #     "param_1": "urgent"
        >>> # }

    Args:
        delimiter: Opening delimiter string (default: "!!")
    """

    def __init__(
        self,
        delimiter: str = "!!",
    ) -> None:
        """Initialize delimiter preamble syntax.

        Args:
            delimiter: Delimiter string to use
        """
        self.delimiter = delimiter
        self._opening_pattern = re.compile(rf"^{re.escape(delimiter)}(\w+):(\w+)(:.+)?$")
        self._closing_pattern = re.compile(rf"^{re.escape(delimiter)}end$")

    def detect_line(self, line: str, candidate: BlockCandidate | None = None) -> DetectionResult:
        """Detect delimiter-based markers."""
        if candidate is None:
            # Looking for opening
            match = self._opening_pattern.match(line)
            if match:
                block_id, block_type, params = match.groups()
                metadata_dict: dict[str, object] = {
                    "id": block_id,
                    "block_type": block_type,
                }

                if params:
                    param_parts = params[1:].split(":")
                    for i, part in enumerate(param_parts):
                        metadata_dict[f"param_{i}"] = part

                return DetectionResult(
                    is_opening=True,
                    metadata=metadata_dict,  # Inline metadata
                )
        # Check for closing
        elif self._closing_pattern.match(line):
            return DetectionResult(is_closing=True)

        return DetectionResult()

    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        """No separate metadata section for this syntax."""
        return False

    def extract_block_type(self, candidate: BlockCandidate) -> str | None:
        """Extract block_type from opening line."""
        if not candidate.lines:
            return None

        # Parse the opening line to get block_type
        detection = self.detect_line(candidate.lines[0], None)
        if detection.metadata and "block_type" in detection.metadata:
            return str(detection.metadata["block_type"])

        return None

    def parse_block(
        self, candidate: BlockCandidate, block_class: type[Any] | None = None
    ) -> ParseResult[BaseMetadata, BaseContent]:
        """Parse the complete block using the specified block class."""

        # Extract metadata and content classes from block_class
        if block_class is None:
            # Default to base classes
            metadata_class = BaseMetadata
            content_class = BaseContent
        else:
            # Extract from block class using type parameters
            metadata_class, content_class = extract_block_types(block_class)

        # Metadata was already extracted during detection
        detection = self.detect_line(candidate.lines[0], None)

        if not detection.metadata:
            return ParseResult(success=False, error="Missing metadata in preamble")

        # Convert all metadata values to strings for type safety
        # Note: id and block_type are always set by detect_line()
        typed_metadata = {k: str(v) for k, v in detection.metadata.items()}

        # Parse metadata using helper
        metadata = self._safe_parse_metadata(metadata_class, typed_metadata)
        if isinstance(metadata, ParseResult):
            return metadata  # Return error

        # Parse content (skip first and last lines)
        content_text = "\n".join(candidate.lines[1:-1])

        # Parse content using helper
        content = self._safe_parse_content(content_class, content_text)
        if isinstance(content, ParseResult):
            return content  # Return error

        return ParseResult(success=True, metadata=metadata, content=content)

    def validate_block(self, _block: ExtractedBlock[BaseMetadata, BaseContent]) -> bool:
        """Additional validation after parsing."""
        return True

    def parse_metadata_early(self, candidate: BlockCandidate) -> dict[str, Any] | None:
        """Parse metadata from inline preamble.

        For this syntax, metadata is extracted from the opening line
        (e.g., !!id:type:param1:param2).
        """
        if not candidate.lines:
            return None

        detection = self.detect_line(candidate.lines[0], None)
        if detection.metadata:
            # Convert all values to strings for consistency
            return {k: str(v) for k, v in detection.metadata.items()}
        return None

    def parse_content_early(self, candidate: BlockCandidate) -> dict[str, Any] | None:
        """Parse content section early.

        Returns raw content dict with the content text.
        """
        if len(candidate.lines) < _MIN_BLOCK_LINES:
            return None

        # Content is all lines except first (header) and last (closing)
        content_lines = candidate.lines[1:-1] if len(candidate.lines) > _MIN_BLOCK_LINES else candidate.lines[1:]
        raw_content = "\n".join(content_lines)
        return {"raw_content": raw_content}


class DelimiterFrontmatterSyntax(BaseSyntax, YAMLFrontmatterMixin):
    """Syntax: Delimiter markers with YAML frontmatter.

    This syntax uses simple delimiter markers with YAML frontmatter for metadata.
    The frontmatter section is delimited by --- markers and must be valid YAML.

    Format:
        !!start
        ---
        id: block_001
        block_type: example
        custom_field: value
        ---
        Content lines here
        !!end

    The YAML frontmatter should include:
        - id: Block identifier (required if using BaseMetadata)
        - block_type: Block type (required if using BaseMetadata)
        - Any additional custom fields defined in your metadata class

    Examples:
        >>> # Simple block with minimal metadata
        >>> '''
        ... !!start
        ... ---
        ... id: msg001
        ... block_type: message
        ... ---
        ... Hello, world!
        ... !!end
        ... '''
        >>>
        >>> # Block with nested YAML metadata
        >>> '''
        ... !!start
        ... ---
        ... id: task001
        ... block_type: task
        ... priority: high
        ... tags:
        ...   - urgent
        ...   - backend
        ... ---
        ... Implement user authentication
        ... !!end
        ... '''

    Args:
        start_delimiter: Opening delimiter string (default: "!!start")
        end_delimiter: Closing delimiter string (default: "!!end")
    """

    def __init__(
        self,
        start_delimiter: str = "!!start",
        end_delimiter: str = "!!end",
    ) -> None:
        """Initialize delimiter frontmatter syntax.

        Args:
            start_delimiter: Starting delimiter
            end_delimiter: Ending delimiter
        """
        self.start_delimiter = start_delimiter
        self.end_delimiter = end_delimiter
        self._frontmatter_pattern = re.compile(r"^---\s*$")

    def detect_line(self, line: str, candidate: BlockCandidate | None = None) -> DetectionResult:
        """Detect delimiter markers and frontmatter boundaries."""
        if candidate is None:
            # Looking for opening
            if line.strip() == self.start_delimiter:
                return DetectionResult(is_opening=True)
        # Inside a block
        elif candidate.current_section == SectionType.HEADER:
            # Should be frontmatter start
            if self._frontmatter_pattern.match(line):
                candidate.transition_to_metadata()
                return DetectionResult(is_metadata_boundary=True)
            # Skip empty lines in header - frontmatter might follow
            if line.strip() == "":
                return DetectionResult()
            # Move directly to content if no frontmatter
            candidate.transition_to_content()
            candidate.content_lines.append(line)
        elif candidate.current_section == SectionType.METADATA:
            if self._frontmatter_pattern.match(line):
                candidate.transition_to_content()
                return DetectionResult(is_metadata_boundary=True)
            candidate.metadata_lines.append(line)
        elif candidate.current_section == SectionType.CONTENT:
            if line.strip() == self.end_delimiter:
                return DetectionResult(is_closing=True)
            candidate.content_lines.append(line)

        return DetectionResult()

    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        """Check if we're still in metadata section."""
        return candidate.current_section in {SectionType.HEADER, SectionType.METADATA}

    def extract_block_type(self, candidate: BlockCandidate) -> str | None:
        """Extract block_type from YAML frontmatter."""
        metadata_dict = self._parse_yaml_metadata(candidate.metadata_lines)
        if metadata_dict and "block_type" in metadata_dict:
            return str(metadata_dict["block_type"])
        return None

    def parse_block(
        self, candidate: BlockCandidate, block_class: type[Any] | None = None
    ) -> ParseResult[BaseMetadata, BaseContent]:
        """Parse the complete block using the specified block class."""

        # Extract metadata and content classes from block_class
        if block_class is None:
            # Default to base classes
            metadata_class = BaseMetadata
            content_class = BaseContent
        else:
            # Extract from block class using type parameters
            metadata_class, content_class = extract_block_types(block_class)

        # Parse metadata from accumulated metadata lines
        metadata_dict, yaml_error = self._parse_yaml_metadata_strict(candidate.metadata_lines)
        if yaml_error:
            return ParseResult(success=False, error=f"YAML parse error: {yaml_error}", exception=yaml_error)

        # Parse metadata using helper
        metadata = self._safe_parse_metadata(metadata_class, metadata_dict)
        if isinstance(metadata, ParseResult):
            return metadata  # Return error

        # Parse content using helper
        content_text = "\n".join(candidate.content_lines)
        content = self._safe_parse_content(content_class, content_text)
        if isinstance(content, ParseResult):
            return content  # Return error

        return ParseResult(success=True, metadata=metadata, content=content)

    def validate_block(self, _block: ExtractedBlock[BaseMetadata, BaseContent]) -> bool:
        """Additional validation after parsing."""
        return True

    def parse_metadata_early(self, candidate: BlockCandidate) -> dict[str, Any] | None:
        """Parse YAML metadata section early.

        Returns parsed YAML frontmatter as a dict.
        """
        return self._parse_yaml_metadata(candidate.metadata_lines)

    def parse_content_early(self, candidate: BlockCandidate) -> dict[str, Any] | None:
        """Parse content section early.

        Returns raw content dict with the content text.
        """
        raw_content = "\n".join(candidate.content_lines)
        return {"raw_content": raw_content}
