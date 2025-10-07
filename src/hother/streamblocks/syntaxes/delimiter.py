"""Delimiter-based syntax implementations."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, cast

import yaml
from pydantic import BaseModel

from hother.streamblocks.core.models import BaseContent, BaseMetadata
from hother.streamblocks.core.types import DetectionResult, ParseResult

if TYPE_CHECKING:
    from hother.streamblocks.core.models import BlockCandidate


class DelimiterPreambleSyntax[TMetadata: BaseModel, TContent: BaseModel]:
    """Syntax: !! delimiter with inline metadata.

    Format: !!<id>:<type>[:param1:param2...]
    """

    def __init__(
        self,
        name: str,
        block_class: type[Any] | None = None,
        delimiter: str = "!!",
    ) -> None:
        """Initialize delimiter preamble syntax.

        Args:
            name: Unique name for this syntax instance
            block_class: BlockDefinition class that defines __metadata_class__ and __content_class__
            delimiter: Delimiter string to use
        """
        self._name = name

        if block_class is None:
            # Default to base classes
            self.metadata_class = cast(type[TMetadata], BaseMetadata)
            self.content_class = cast(type[TContent], BaseContent)
        else:
            # Extract metadata and content classes from block class
            self.metadata_class = cast(
                type[TMetadata], getattr(block_class, "__metadata_class__", BaseMetadata)
            )
            self.content_class = cast(type[TContent], getattr(block_class, "__content_class__", BaseContent))

        self.delimiter = delimiter
        self._opening_pattern = re.compile(rf"^{re.escape(delimiter)}(\w+):(\w+)(:.+)?$")
        self._closing_pattern = re.compile(rf"^{re.escape(delimiter)}end$")

    @property
    def name(self) -> str:
        """Get syntax name."""
        return self._name

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

    def parse_block(self, candidate: BlockCandidate) -> ParseResult[TMetadata, TContent]:
        """Parse the complete block."""

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
            metadata = self.metadata_class(**typed_metadata)
        except Exception as e:
            return ParseResult(success=False, error=f"Invalid metadata: {e}")

        # Parse content (skip first and last lines)
        content_text = "\n".join(candidate.lines[1:-1])

        try:
            # All content classes must have parse method
            content = cast("TContent", self.content_class.parse(content_text))  # type: ignore[attr-defined]
        except Exception as e:
            return ParseResult(success=False, error=f"Invalid content: {e}")

        return ParseResult(success=True, metadata=metadata, content=content)

    def validate_block(self, metadata: TMetadata, content: TContent) -> bool:
        """Additional validation after parsing."""
        return True


class DelimiterFrontmatterSyntax[TMetadata: BaseModel, TContent: BaseModel]:
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
        name: str,
        block_class: type[Any] | None = None,
        start_delimiter: str = "!!start",
        end_delimiter: str = "!!end",
    ) -> None:
        """Initialize delimiter frontmatter syntax.

        Args:
            name: Unique name for this syntax instance
            block_class: BlockDefinition class that defines __metadata_class__ and __content_class__
            start_delimiter: Starting delimiter
            end_delimiter: Ending delimiter
        """
        self._name = name

        if block_class is None:
            # Default to base classes
            self.metadata_class = cast(type[TMetadata], BaseMetadata)
            self.content_class = cast(type[TContent], BaseContent)
        else:
            # Extract metadata and content classes from block class
            self.metadata_class = cast(
                type[TMetadata], getattr(block_class, "__metadata_class__", BaseMetadata)
            )
            self.content_class = cast(type[TContent], getattr(block_class, "__content_class__", BaseContent))

        self.start_delimiter = start_delimiter
        self.end_delimiter = end_delimiter
        self._frontmatter_pattern = re.compile(r"^---\s*$")

    @property
    def name(self) -> str:
        """Get syntax name."""
        return self._name

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
                metadata_dict["block_type"] = "unknown"

        try:
            # Convert all metadata values to proper types for type safety
            typed_metadata = {k: str(v) if not isinstance(v, str) else v for k, v in metadata_dict.items()}
            metadata = self.metadata_class(**typed_metadata)
        except Exception as e:
            return ParseResult(success=False, error=f"Invalid metadata: {e}")

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
