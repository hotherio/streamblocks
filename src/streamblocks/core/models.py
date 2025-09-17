"""Block models for StreamBlocks."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Generic

from pydantic import BaseModel, ConfigDict, Field

from .types import BlockState, TContent, TMetadata

if TYPE_CHECKING:
    from .types import BlockSyntax


class BlockCandidate:
    """Represents a potential block being accumulated during stream processing.

    A BlockCandidate tracks the state of block detection and accumulation,
    maintaining separate collections for metadata and content lines as the
    block is built from the stream.

    Attributes:
        syntax: The BlockSyntax instance that detected this candidate
        start_line: The line number where this block started
        lines: All accumulated lines (raw text)
        state: Current processing state from BlockState enum
        metadata_lines: Lines that belong to the metadata section
        content_lines: Lines that belong to the content section
        current_section: Current section being accumulated ("header", "metadata", "content")
    """

    def __init__(self, syntax: BlockSyntax, start_line: int) -> None:
        """Initialize a new block candidate.

        Args:
            syntax: The BlockSyntax instance that detected this block
            start_line: The line number where this block starts
        """
        self.syntax = syntax
        self.start_line = start_line
        self.lines: list[str] = []
        self.state = BlockState.HEADER_DETECTED
        self.metadata_lines: list[str] = []
        self.content_lines: list[str] = []
        self.current_section: str = "header"

    def add_line(self, line: str) -> None:
        """Add a line to this candidate.

        The line is added to the appropriate section based on current_section.

        Args:
            line: The line to add (without newline)
        """
        self.lines.append(line)

        if self.current_section == "metadata":
            self.metadata_lines.append(line)
        elif self.current_section == "content":
            self.content_lines.append(line)

    @property
    def raw_text(self) -> str:
        """Get the complete raw text of this candidate.

        Returns:
            All accumulated lines joined with newlines
        """
        return "\n".join(self.lines)

    def compute_hash(self) -> str:
        """Compute a hash ID for this block based on its content.

        Uses the first 64 characters of raw_text to generate a SHA256 hash,
        returning the first 8 characters of the hex digest.

        Returns:
            8-character hash ID string
        """
        # Use first 64 chars of raw text for hash
        hash_input = self.raw_text[:64]
        hash_obj = hashlib.sha256(hash_input.encode("utf-8"))
        # Return first 8 chars of hex digest
        return hash_obj.hexdigest()[:8]


class Block(BaseModel, Generic[TMetadata, TContent]):
    """Represents a validated and extracted block.

    A Block contains the parsed metadata and content along with
    position information and a unique hash ID.

    Type Parameters:
        TMetadata: The metadata model type (must extend BaseModel)
        TContent: The content model type (must extend BaseModel)

    Attributes:
        syntax_name: Name of the syntax that extracted this block
        metadata: Parsed and validated metadata
        content: Parsed and validated content
        raw_text: Original raw text of the block
        line_start: Starting line number (inclusive)
        line_end: Ending line number (inclusive)
        hash_id: Unique hash identifier for this block
    """

    syntax_name: str = Field(..., description="Name of the syntax that extracted this block")
    metadata: TMetadata = Field(..., description="Parsed and validated metadata")
    content: TContent = Field(..., description="Parsed and validated content")
    raw_text: str = Field(..., description="Original raw text of the block")
    line_start: int = Field(..., description="Starting line number (inclusive)")
    line_end: int = Field(..., description="Ending line number (inclusive)")
    hash_id: str = Field(..., description="Unique hash identifier for this block")

    model_config = ConfigDict(arbitrary_types_allowed=True)
