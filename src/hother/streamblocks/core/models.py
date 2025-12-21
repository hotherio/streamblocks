"""Core models for StreamBlocks."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any, Generic, TypeVar, get_args, get_origin

from pydantic import BaseModel, Field

from hother.streamblocks.core.types import BaseContent, BaseMetadata, BlockState, TContent, TMetadata

if TYPE_CHECKING:
    from hother.streamblocks.syntaxes.base import BaseSyntax


def extract_block_types(block_class: type[Any]) -> tuple[type[BaseMetadata], type[BaseContent]]:
    """Extract metadata and content type parameters from a Block class.

    Handles multiple patterns:
    1. Concrete classes with Pydantic model_fields
    2. Generic type aliases like Block[MetadataClass, ContentClass]
    3. Classes inheriting from Block[M, C]

    Args:
        block_class: The block class to extract types from

    Returns:
        Tuple of (metadata_class, content_class)
    """
    # Method 1: Try Pydantic model_fields (for concrete classes)
    if hasattr(block_class, "model_fields"):
        metadata_field = block_class.model_fields.get("metadata")
        content_field = block_class.model_fields.get("content")

        if metadata_field and content_field:
            metadata_type = metadata_field.annotation
            content_type = content_field.annotation
            # Verify we got actual types, not just the generic TypeVar
            if (
                metadata_type is not None
                and content_type is not None
                and not isinstance(metadata_type, TypeVar)
                and not isinstance(content_type, TypeVar)
            ):
                return (metadata_type, content_type)

    # Method 2: Try get_args() for generic type aliases like Block[M, C]
    args = get_args(block_class)
    if len(args) >= 2:
        metadata_type, content_type = args[0], args[1]
        try:
            if issubclass(metadata_type, BaseMetadata) and issubclass(content_type, BaseContent):
                return (metadata_type, content_type)
        except TypeError:
            # issubclass can raise TypeError for non-class types
            pass

    # Method 3: Check __orig_bases__ for inherited generics
    if hasattr(block_class, "__orig_bases__"):
        for base in block_class.__orig_bases__:
            origin = get_origin(base)
            if origin is Block or origin is ExtractedBlock:
                args = get_args(base)
                if len(args) >= 2:
                    return (args[0], args[1])

    # Fallback to base classes
    return (BaseMetadata, BaseContent)


class BlockCandidate:
    """Tracks a potential block being accumulated."""

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


class Block(BaseModel, Generic[TMetadata, TContent]):
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
