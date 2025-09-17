"""Patch/diff content models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .base import BaseContent


class PatchContent(BaseContent):
    """Content model for patch/diff blocks."""

    diff: str = Field(..., description="The patch content in unified diff format")

    @field_validator("diff")
    @classmethod
    def validate_diff_format(cls, v: str) -> str:
        """Validate that the diff is in proper unified diff format."""
        if not v.strip():
            raise ValueError("Diff content cannot be empty")

        # Check for basic unified diff markers
        lines = v.strip().split("\n")
        has_range_marker = any(line.startswith("@@") for line in lines)

        if not has_range_marker:
            raise ValueError("Invalid diff format: missing @@ range markers")

        return v

    @classmethod
    def parse(cls, text: str) -> PatchContent:
        """Parse patch content from text.

        Validates that the text is in unified diff format with @@ markers.

        Args:
            text: Raw patch/diff text

        Returns:
            Parsed PatchContent instance

        Raises:
            ValueError: If text is not valid unified diff format
        """
        return cls(diff=text)


class PatchMetadata(BaseModel):
    """Metadata model for patch blocks."""

    id: str = Field(..., description="Block identifier")
    block_type: Literal["patch"] = Field(default="patch", description="Type of block")
    file_path: str = Field(..., description="Path to the file being patched")
    description: str | None = Field(default=None, description="Optional description of the patch")
