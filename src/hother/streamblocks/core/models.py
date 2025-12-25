"""Core models for StreamBlocks."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from hother.streamblocks.core.types import BaseContent, BaseMetadata, BlockState

if TYPE_CHECKING:
    from hother.streamblocks.syntaxes.base import BaseSyntax


def extract_block_types(block_class: type[Any]) -> tuple[type[BaseMetadata], type[BaseContent]]:
    """Extract metadata and content type parameters from a Block class.

    For classes inheriting from Block[M, C], Pydantic resolves the concrete
    types and stores them in the field annotations. We simply extract them
    from the model_fields.

    Args:
        block_class: The block class to extract types from

    Returns:
        Tuple of (metadata_class, content_class)
    """
    # Extract from Pydantic field annotations
    if issubclass(block_class, BaseModel):
        metadata_field = block_class.model_fields.get("metadata")
        content_field = block_class.model_fields.get("content")

        if (
            metadata_field
            and content_field
            and metadata_field.annotation is not None
            and content_field.annotation is not None
        ):
            return (metadata_field.annotation, content_field.annotation)

    # Fallback to base classes
    return (BaseMetadata, BaseContent)


class BlockCandidate:
    """Tracks a potential block being accumulated."""

    __slots__ = (
        "content_lines",
        "content_validation_error",
        "content_validation_passed",
        "current_section",
        "lines",
        "metadata_lines",
        "metadata_validation_error",
        "metadata_validation_passed",
        "parsed_content",
        "parsed_metadata",
        "start_line",
        "state",
        "syntax",
    )

    def __init__(self, syntax: BaseSyntax, start_line: int) -> None:
        """Initialize a new block candidate.

        Args:
            syntax: The syntax handler for this block
            start_line: Line number where the block started
        """
        self.syntax = syntax
        self.start_line = start_line
        self.lines: list[str] = []
        self.state = BlockState.HEADER_DETECTED
        self.metadata_lines: list[str] = []
        self.content_lines: list[str] = []
        self.current_section: str = "header"  # "header", "metadata", "content"

        # Cache fields for early parsing results
        self.parsed_metadata: dict[str, Any] | None = None
        self.parsed_content: dict[str, Any] | None = None

        # Validation state for section end events
        self.metadata_validation_passed: bool = True
        self.metadata_validation_error: str | None = None
        self.content_validation_passed: bool = True
        self.content_validation_error: str | None = None

    def add_line(self, line: str) -> None:
        """Add a line to the candidate."""
        self.lines.append(line)

    @property
    def raw_text(self) -> str:
        """Get the raw text of all accumulated lines."""
        return "\n".join(self.lines)

    def compute_hash(self) -> str:
        """Compute hash of first 64 chars for ID."""
        text_slice = self.raw_text[:64]
        return hashlib.sha256(text_slice.encode()).hexdigest()[:8]

    def __repr__(self) -> str:
        """Return a developer-friendly string representation."""
        return (
            f"BlockCandidate(syntax={type(self.syntax).__name__}, "
            f"start_line={self.start_line}, state={self.state.value}, "
            f"lines={len(self.lines)}, section={self.current_section!r})"
        )


class Block[TMetadata: BaseMetadata, TContent: BaseContent](BaseModel):
    """User-facing base class for defining block types.

    This minimal class contains only the essential fields (metadata and content).
    Users inherit from this to define their block types.

    Usage:
        class YesNo(Block[YesNoMetadata, YesNoContent]):
            pass

        # Access fields
        block: Block[YesNoMetadata, YesNoContent]
        block.metadata.prompt  # Type-safe access to metadata fields
        block.content.response  # Type-safe access to content fields
    """

    metadata: TMetadata = Field(..., description="Parsed block metadata")
    content: TContent = Field(..., description="Parsed block content")


class ExtractedBlock[TMetadata: BaseMetadata, TContent: BaseContent](Block[TMetadata, TContent]):
    """Full runtime representation of an extracted block.

    This class extends the minimal Block with extraction metadata like
    line numbers, syntax name, and hash ID. The processor creates instances
    of this class when blocks are successfully extracted.

    The metadata and content fields are typed generics, allowing type-safe
    access to block-specific fields.
    """

    syntax_name: str = Field(..., description="Name of the syntax that extracted this block")
    raw_text: str = Field(..., description="Original raw text of the block")
    line_start: int = Field(..., description="Starting line number")
    line_end: int = Field(..., description="Ending line number")
    hash_id: str = Field(..., description="Hash-based ID for the block")
