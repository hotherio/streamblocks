"""Protocol definitions for StreamBlocks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from hother.streamblocks.core.types import DetectionResult, ParseResult, TContent, TMetadata

if TYPE_CHECKING:
    from hother.streamblocks.core.models import BlockCandidate


class BlockSyntax(Protocol[TMetadata, TContent]):
    """Protocol for defining block syntax parsers."""

    @property
    def name(self) -> str:
        """Get unique syntax identifier."""
        ...

    def detect_line(self, line: str, candidate: BlockCandidate | None) -> DetectionResult:
        """Detect if line is significant for this syntax.

        Args:
            line: Current line to check
            candidate: Current candidate if we're inside a block, None if searching

        Returns:
            DetectionResult indicating what was detected
        """
        ...

    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        """Check if syntax expects more metadata lines.

        Args:
            candidate: The current block candidate

        Returns:
            True if more metadata lines are expected
        """
        ...

    def parse_block(self, candidate: BlockCandidate) -> ParseResult[TMetadata, TContent]:
        """Parse a complete block candidate.

        Args:
            candidate: The complete block candidate to parse

        Returns:
            ParseResult with parsed metadata and content or error
        """
        ...

    def validate_block(self, metadata: TMetadata, content: TContent) -> bool:
        """Additional validation after parsing.

        Args:
            metadata: Parsed metadata
            content: Parsed content

        Returns:
            True if the block is valid
        """
        ...
