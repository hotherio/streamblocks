"""Core models for StreamBlocks."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Generic

from pydantic import BaseModel, Field

from hother.streamblocks.core.types import BlockState, TContent, TMetadata

if TYPE_CHECKING:
    from hother.streamblocks.core.protocols import BlockSyntax


class BlockConfig:
    """Configuration holder for block type registration.

    Used to link metadata and content classes for a block type.
    Subclass this to create block type configurations for the registry.

    Example:
        class FileOperations(BlockConfig):
            __metadata_class__ = FileOperationsMetadata
            __content_class__ = FileOperationsContent
    """

    # Class attributes for metadata/content classes - subclasses should override
    __metadata_class__: type[BaseModel]
    __content_class__: type[BaseModel]


class BaseMetadata(BaseModel):
    """Base metadata model with standard fields.

    All custom metadata models should inherit from this class.
    """

    id: str = Field(..., description="Block identifier")
    block_type: str = Field(..., description="Type of the block")


class BaseContent(BaseModel):
    """Base content model with raw content field.

    All custom content models should inherit from this class.
    The raw_content field always contains the unparsed block content.
    """

    raw_content: str = Field(..., description="Raw unparsed content from the block")

    @classmethod
    def parse(cls, raw_text: str) -> BaseContent:
        """Default parse method that just stores raw content.

        Override this in subclasses to add custom parsing logic.
        """
        return cls(raw_content=raw_text)


class BlockCandidate:
    """Tracks a potential block being accumulated."""

    def __init__(self, syntax: BlockSyntax[TMetadata, TContent], start_line: int) -> None:
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


class BlockDefinition(BaseModel, Generic[TMetadata, TContent]):
    """Extracted block with parsed metadata and content.

    This is the envelope containing the parsed metadata and data plus
    extraction/processing information.

    The metadata and data fields are typed generics, allowing type-safe
    access to block-specific fields.

    Example:
        block: BlockDefinition[FileOperationsMetadata, FileOperationsContent]
        block.metadata.id  # Type-safe access to metadata fields
        block.data.operations  # Type-safe access to content fields
    """

    metadata: TMetadata = Field(..., description="Parsed block metadata")
    data: TContent = Field(..., description="Parsed block data/content")
    syntax_name: str = Field(..., description="Name of the syntax that extracted this block")
    raw_text: str = Field(..., description="Original raw text of the block")
    line_start: int = Field(..., description="Starting line number")
    line_end: int = Field(..., description="Ending line number")
    hash_id: str = Field(..., description="Hash-based ID for the block")
