"""YAML frontmatter syntax implementation.

This syntax handles blocks in the format:
---
key: value
metadata: here
---
Content goes here
"""

from __future__ import annotations

from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from streamblocks.syntaxes.abc import FrontmatterSyntax


class YAMLMetadata(BaseModel):
    """Metadata model for YAML frontmatter blocks."""

    model_config = ConfigDict(extra="allow", validate_assignment=True)

    id: str | None = Field(None, description="Optional block identifier")
    type: str | None = Field(None, description="Block type or category")
    title: str | None = Field(None, description="Block title")
    author: str | None = Field(None, description="Block author")
    tags: list[str] = Field(default_factory=list, description="Block tags")
    extra_fields: dict[str, Any] = Field(default_factory=dict, description="Additional fields")

    def __init__(self, **data: Any) -> None:
        """Initialize with dynamic field handling."""
        # Known fields
        known_fields = {"id", "type", "title", "author", "tags"}

        # Separate known and extra fields
        known_data = {k: v for k, v in data.items() if k in known_fields}
        extra_data = {k: v for k, v in data.items() if k not in known_fields}

        # Initialize with known fields
        super().__init__(**known_data)

        # Store extra fields
        self.extra_fields = extra_data


class YAMLContent(BaseModel):
    """Content model for YAML frontmatter blocks."""

    model_config = ConfigDict(validate_assignment=True)

    text: str = Field(description="The content text")
    format: str = Field(default="markdown", description="Content format")

    @property
    def lines(self) -> list[str]:
        """Get content as list of lines."""
        return self.text.splitlines()

    @property
    def is_empty(self) -> bool:
        """Check if content is empty."""
        return not self.text.strip()


class YAMLFrontmatterSyntax(FrontmatterSyntax[YAMLMetadata, YAMLContent]):
    """YAML frontmatter syntax parser.

    Handles blocks like:
    ---
    id: my-block
    type: document
    tags: [python, example]
    ---
    # My Document
    This is the content...
    """

    @property
    def name(self) -> str:
        """Syntax identifier."""
        return "yaml-frontmatter"

    def parse_metadata(self, yaml_text: str) -> YAMLMetadata:
        """Parse YAML text into metadata model."""
        if not yaml_text.strip():
            # Empty metadata section
            return YAMLMetadata()

        # Parse YAML
        try:
            data = yaml.safe_load(yaml_text)
            if data is None:
                return YAMLMetadata()
            if not isinstance(data, dict):
                raise ValueError(f"Expected dict, got {type(data).__name__}")
            return YAMLMetadata(**data)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML metadata: {e}") from e

    def parse_content(self, content_text: str) -> YAMLContent:
        """Parse content text into content model."""
        # Try to detect format from metadata or content
        format_hint = "markdown"  # Default

        # Simple format detection based on content
        if content_text.strip():
            lines = content_text.strip().splitlines()
            if lines and lines[0].startswith("```"):
                format_hint = "code"
            elif any(line.startswith("#") for line in lines[:5]):
                format_hint = "markdown"
            elif content_text.strip().startswith("<"):
                format_hint = "html"

        return YAMLContent(text=content_text, format=format_hint)

    def get_block_type_hints(self) -> list[str]:
        """Get list of block types this syntax typically produces."""
        return ["document", "metadata", "frontmatter", "yaml"]

    def validate_block(self, metadata: YAMLMetadata, content: YAMLContent) -> bool:
        """Validate parsed block."""
        # Basic validation - at least one of metadata or content should be non-empty
        has_metadata = bool(
            metadata.id
            or metadata.type
            or metadata.title
            or metadata.author
            or metadata.tags
            or metadata.extra_fields
        )
        has_content = not content.is_empty

        return has_metadata or has_content
