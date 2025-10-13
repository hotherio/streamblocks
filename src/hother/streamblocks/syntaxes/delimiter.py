"""Delimiter-based syntax implementations."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Protocol

import yaml

from hother.streamblocks.core.models import extract_block_types
from hother.streamblocks.core.types import BaseContent, BaseMetadata, DetectionResult, ParseResult
from hother.streamblocks.syntaxes.base import BaseSyntax

if TYPE_CHECKING:
    from hother.streamblocks.core.models import BlockCandidate, ExtractedBlock


class ContentParser(Protocol):
    """Protocol for content classes with a parse method."""

    @classmethod
    def parse(cls, raw_text: str) -> BaseContent:
        """Parse raw text into content."""
        ...


class DelimiterPreambleSyntax(BaseSyntax):
    """Syntax: !! delimiter with inline metadata.

    Format: !!<id>:<type>[:param1:param2...]
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

        try:
            # Ensure id and block_type are in metadata dict
            if "id" not in detection.metadata:
                detection.metadata["id"] = str(detection.metadata.get("block_id", "unknown"))
            if "block_type" not in detection.metadata:
                detection.metadata["block_type"] = str(detection.metadata.get("type", "unknown"))

            # Convert all metadata values to strings for type safety
            typed_metadata = {k: str(v) for k, v in detection.metadata.items()}
            metadata = metadata_class(**typed_metadata)
        except Exception as e:
            return ParseResult(success=False, error=f"Invalid metadata: {e}", exception=e)

        # Parse content (skip first and last lines)
        content_text = "\n".join(candidate.lines[1:-1])

        try:
            # All content classes must have parse method
            content = content_class.parse(content_text)
        except Exception as e:
            return ParseResult(success=False, error=f"Invalid content: {e}", exception=e)

        return ParseResult(success=True, metadata=metadata, content=content)

    def serialize_block(self, block: Any) -> str:
        """Serialize block to delimiter preamble format.

        Args:
            block: Block instance with metadata and content

        Returns:
            String in !!id:type format with content

        Example:
            !!file01:files_operations
            src/main.py:C
            !!end
        """
        # Extract metadata fields
        metadata = block.metadata
        block_id = metadata.id
        block_type = metadata.block_type

        # Build opening line: !!id:type
        opening = f"{self.delimiter}{block_id}:{block_type}"

        # Add any extra params if present (param_0, param_1, etc.)
        params = []
        i = 0
        while hasattr(metadata, f"param_{i}"):
            params.append(str(getattr(metadata, f"param_{i}")))
            i += 1
        if params:
            opening += ":" + ":".join(params)

        # Get content as string
        content = block.content.raw_content

        # Build full block
        closing = f"{self.delimiter}end"
        return f"{opening}\n{content}\n{closing}"

    def describe_format(self) -> str:
        """Describe delimiter preamble format."""
        return f"""Delimiter Preamble Syntax

Format:
{self.delimiter}<id>:<type>[:<param1>:<param2>...]
content lines
{self.delimiter}end

Components:
- Opening line: {self.delimiter}<id>:<type> where id is unique and type identifies the block
- Optional parameters: Additional colon-separated values after type
- Content: Any text content between opening and closing
- Closing line: {self.delimiter}end"""

    def validate_block(self, _block: ExtractedBlock[BaseMetadata, BaseContent]) -> bool:
        """Additional validation after parsing."""
        return True


class DelimiterFrontmatterSyntax(BaseSyntax):
    """Syntax: Delimiter markers with YAML frontmatter.

    Format:
    !!start
    ---
    key: value
    ---
    content
    !!end
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
        elif candidate.current_section == "header":
            # Should be frontmatter start
            if self._frontmatter_pattern.match(line):
                candidate.current_section = "metadata"
                return DetectionResult(is_metadata_boundary=True)
            # Skip empty lines in header - frontmatter might follow
            if line.strip() == "":
                return DetectionResult()
            # Move directly to content if no frontmatter
            candidate.current_section = "content"
            candidate.content_lines.append(line)
        elif candidate.current_section == "metadata":
            if self._frontmatter_pattern.match(line):
                candidate.current_section = "content"
                return DetectionResult(is_metadata_boundary=True)
            candidate.metadata_lines.append(line)
        elif candidate.current_section == "content":
            if line.strip() == self.end_delimiter:
                return DetectionResult(is_closing=True)
            candidate.content_lines.append(line)

        return DetectionResult()

    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        """Check if we're still in metadata section."""
        return candidate.current_section in ["header", "metadata"]

    def extract_block_type(self, candidate: BlockCandidate) -> str | None:
        """Extract block_type from YAML frontmatter."""
        if not candidate.metadata_lines:
            return None

        # Parse YAML to extract block_type
        yaml_content = "\n".join(candidate.metadata_lines)
        try:
            metadata_dict: dict[str, Any] = yaml.safe_load(yaml_content) or {}
            return str(metadata_dict.get("block_type")) if "block_type" in metadata_dict else None
        except Exception:
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
        metadata_dict: dict[str, Any] = {}
        if candidate.metadata_lines:
            yaml_content = "\n".join(candidate.metadata_lines)
            try:
                metadata_dict = yaml.safe_load(yaml_content) or {}
            except Exception as e:
                return ParseResult(success=False, error=f"Invalid YAML: {e}", exception=e)

        # Ensure id and block_type have defaults
        # Only fill in defaults if using BaseMetadata (no custom class provided)
        if metadata_class is BaseMetadata:
            if "id" not in metadata_dict:
                # Generate an ID based on hash of content
                metadata_dict["id"] = f"block_{candidate.compute_hash()}"
            if "block_type" not in metadata_dict:
                metadata_dict["block_type"] = "unknown"

        try:
            # Pass metadata dict directly to Pydantic for validation
            metadata = metadata_class(**metadata_dict)
        except Exception as e:
            return ParseResult(success=False, error=f"Invalid metadata: {e}", exception=e)

        content_text = "\n".join(candidate.content_lines)

        try:
            # All content classes must have parse method
            content = content_class.parse(content_text)
        except Exception as e:
            return ParseResult(success=False, error=f"Invalid content: {e}", exception=e)

        return ParseResult(success=True, metadata=metadata, content=content)

    def serialize_block(self, block: Any) -> str:
        """Serialize block to delimiter frontmatter format.

        Args:
            block: Block instance with metadata and content

        Returns:
            String in !!start format with YAML frontmatter

        Example:
            !!start
            ---
            id: file01
            block_type: files_operations
            ---
            src/main.py:C
            !!end
        """
        # Convert metadata to dict and then to YAML
        metadata_dict = block.metadata.model_dump()
        metadata_yaml = yaml.dump(metadata_dict, default_flow_style=False, sort_keys=False)

        # Get content
        content = block.content.raw_content

        # Build full block
        return f"{self.start_delimiter}\n---\n{metadata_yaml}---\n{content}\n{self.end_delimiter}"

    def describe_format(self) -> str:
        """Describe delimiter frontmatter format."""
        return f"""Delimiter Frontmatter Syntax

Format:
{self.start_delimiter}
---
key: value
---
content lines
{self.end_delimiter}

Components:
- Opening line: {self.start_delimiter}
- Metadata section: YAML frontmatter between --- delimiters
- Content: Any text content after metadata
- Closing line: {self.end_delimiter}"""

    def validate_block(self, _block: ExtractedBlock[BaseMetadata, BaseContent]) -> bool:
        """Additional validation after parsing."""
        return True
