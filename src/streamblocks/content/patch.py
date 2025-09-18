"""Patch content models."""

from typing import Literal

from pydantic import BaseModel, Field

from streamblocks.core.models import BaseContent, BaseMetadata


class PatchContent(BaseContent):
    """Content model for patch blocks."""

    diff: str = Field(..., description="The patch diff content")

    @classmethod
    def parse(cls, raw_text: str) -> "PatchContent":
        """Parse and validate patch content."""
        # Basic validation
        if not raw_text.strip():
            raise ValueError("Empty patch")

        # For now, accept any content that looks like it has changes
        # (lines starting with +, -, or space for context)
        lines = raw_text.strip().split("\n")
        has_diff_lines = any(line.startswith("+") or line.startswith("-") or line.startswith(" ") for line in lines)

        if not has_diff_lines:
            # If no obvious diff markers, just accept it as is
            # This allows for more flexible patch formats
            pass

        return cls(raw_content=raw_text, diff=raw_text.strip())


class PatchMetadata(BaseMetadata):
    """Metadata for patch blocks."""

    # Override block_type with specific literal
    block_type: Literal["patch"] = "patch"  # type: ignore[assignment]
    type: Literal["patch"] = "patch"  # Alias for compatibility
    file: str  # Changed from file_path for consistency with examples
    start_line: int | None = None
    author: str | None = None
    priority: str | None = None
    description: str | None = None
