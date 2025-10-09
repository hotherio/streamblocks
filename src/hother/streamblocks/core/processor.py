"""Stream processing engine for StreamBlocks."""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from hother.streamblocks.core.models import BlockCandidate, ExtractedBlock
from hother.streamblocks.core.types import (
    BaseContent,
    BaseMetadata,
    BlockDeltaEvent,
    BlockExtractedEvent,
    BlockRejectedEvent,
    BlockState,
    RawTextEvent,
    StreamEvent,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator

    from hother.streamblocks.core.registry import Registry


def _get_syntax_name(syntax: object) -> str:
    """Get the name of a syntax from its class name."""
    return type(syntax).__name__


class StreamBlockProcessor:
    """Main stream processing engine for a single syntax type.

    This processor works with exactly one syntax.
    """

    def __init__(
        self,
        registry: Registry,
        lines_buffer: int = 5,
        max_line_length: int = 16_384,
        max_block_size: int = 1_048_576,  # 1MB
    ) -> None:
        """Initialize the stream processor.

        Args:
            registry: Registry with a single syntax
            lines_buffer: Number of lines to keep in buffer
            max_line_length: Maximum line length before truncation
            max_block_size: Maximum block size in bytes
        """
        self.registry = registry
        self.syntax = registry.syntax  # Direct access to the syntax
        self.lines_buffer = lines_buffer
        self.max_line_length = max_line_length
        self.max_block_size = max_block_size

        # Processing state
        self._buffer: deque[str] = deque(maxlen=lines_buffer)
        self._candidates: list[BlockCandidate] = []
        self._line_counter = 0
        self._accumulated_text: list[str] = []

    async def process_stream(
        self,
        stream: AsyncIterator[str],
    ) -> AsyncGenerator[StreamEvent[BaseMetadata, BaseContent]]:
        """Process stream and yield events.

        Args:
            stream: Async iterator yielding text chunks

        Yields:
            StreamEvent objects for different processing stages
        """
        async for chunk in stream:
            # Accumulate chunks until we have complete lines
            self._accumulated_text.append(chunk)

            # Check if we have complete lines
            text = "".join(self._accumulated_text)
            lines = text.split("\n")

            # Keep incomplete line for next iteration
            if not text.endswith("\n"):
                self._accumulated_text = [lines[-1]]
                lines = lines[:-1]
            else:
                self._accumulated_text = []

            # Process complete lines
            for line in lines:
                # Enforce max line length
                truncated_line = line[: self.max_line_length] if len(line) > self.max_line_length else line

                self._line_counter += 1

                # Process line through detection pipeline
                async for event in self._process_line(truncated_line):
                    yield event

        # Flush remaining candidates at stream end
        async for event in self._flush_candidates():
            yield event

    async def _process_line(
        self,
        line: str,
    ) -> AsyncGenerator[StreamEvent[BaseMetadata, BaseContent]]:
        """Process a single line through detection.

        Args:
            line: Line to process

        Yields:
            StreamEvent objects
        """
        # Add to buffer
        self._buffer.append(line)

        # First, check active candidates
        handled_by_candidate = False

        for candidate in list(self._candidates):
            # Let the syntax check this line in context
            detection = candidate.syntax.detect_line(line, candidate)

            if detection.is_closing:
                # Found closing marker
                candidate.add_line(line)
                candidate.state = BlockState.CLOSING_DETECTED

                # Try to extract block
                event = await self._try_extract_block(candidate)
                yield event
                self._candidates.remove(candidate)
                handled_by_candidate = True

            elif detection.is_metadata_boundary:
                # Syntax detected a metadata boundary
                candidate.add_line(line)
                # Syntax may update candidate.current_section internally

                # Emit delta event
                yield BlockDeltaEvent(
                    data=line,
                    syntax=_get_syntax_name(candidate.syntax),
                    start_line=candidate.start_line,
                    current_line=self._line_counter,
                    section=candidate.current_section,
                    delta=line,
                    accumulated=candidate.raw_text,
                )
                handled_by_candidate = True

            else:
                # Regular line inside block
                candidate.add_line(line)

                # Check size limit
                if len(candidate.raw_text) > self.max_block_size:
                    yield self._create_rejection_event(
                        candidate,
                        "Block size exceeded",
                    )
                    self._candidates.remove(candidate)
                    handled_by_candidate = True
                    continue

                # The syntax's detect_line may have updated internal state
                # (e.g., added to metadata_lines or content_lines)

                # Emit delta event
                yield BlockDeltaEvent(
                    data=line,
                    syntax=_get_syntax_name(candidate.syntax),
                    start_line=candidate.start_line,
                    current_line=self._line_counter,
                    section=candidate.current_section,
                    delta=line,
                    accumulated=candidate.raw_text,
                )
                handled_by_candidate = True

        # If not handled by any candidate, check for new block openings
        if not handled_by_candidate:
            opening_found = False

            # Check if this line opens a new block
            detection = self.syntax.detect_line(line, None)

            if detection.is_opening:
                # Start new candidate
                candidate = BlockCandidate(self.syntax, self._line_counter)
                candidate.add_line(line)

                # If syntax provided inline metadata, store it
                if detection.metadata:
                    # This is for syntaxes like DelimiterPreamble
                    # that extract metadata from the opening line
                    candidate.metadata_lines = [str(detection.metadata)]

                self._candidates.append(candidate)
                opening_found = True

            # If no candidates and no openings, emit raw text
            if not opening_found:
                yield RawTextEvent(
                    data=line,
                    line_number=self._line_counter,
                )

    async def _try_extract_block(
        self,
        candidate: BlockCandidate,
    ) -> BlockExtractedEvent[BaseMetadata, BaseContent] | BlockRejectedEvent[BaseMetadata, BaseContent]:
        """Try to parse and validate a complete block.

        Args:
            candidate: Block candidate to extract

        Returns:
            BlockExtractedEvent if successful, BlockRejectedEvent if validation fails
        """
        # Step 1: Extract block_type from candidate
        block_type = candidate.syntax.extract_block_type(candidate)

        # Step 2: Look up block_class from registry
        block_class = None
        if block_type:
            block_class = self.registry.get_block_class(block_type)

        # Step 3: Parse with the appropriate block_class
        parse_result = candidate.syntax.parse_block(candidate, block_class)

        if not parse_result.success:
            error = parse_result.error or "Parse failed"
            return self._create_rejection_event(candidate, error, parse_result.exception)

        metadata = parse_result.metadata
        content = parse_result.content

        if metadata is None or content is None:
            return self._create_rejection_event(candidate, "Missing metadata or content")

        # Create extracted block with metadata, content, and extraction info
        block = ExtractedBlock(
            metadata=metadata,
            content=content,
            syntax_name=_get_syntax_name(candidate.syntax),
            raw_text=candidate.raw_text,
            line_start=candidate.start_line,
            line_end=self._line_counter,
            hash_id=candidate.compute_hash(),
        )

        # Additional validation from syntax
        if not candidate.syntax.validate_block(block):
            return self._create_rejection_event(candidate, "Syntax validation failed")

        # Registry validation (user-defined validators)
        if not self.registry.validate_block(block):
            return self._create_rejection_event(candidate, "Registry validation failed")

        return BlockExtractedEvent(
            data=candidate.raw_text,
            block=block,
        )

    def _create_rejection_event(
        self,
        candidate: BlockCandidate,
        reason: str = "Validation failed",
        exception: Exception | None = None,
    ) -> BlockRejectedEvent[BaseMetadata, BaseContent]:
        """Create a rejection event.

        Args:
            candidate: Rejected candidate
            reason: Reason for rejection
            exception: Optional exception that caused rejection

        Returns:
            BLOCK_REJECTED event
        """
        return BlockRejectedEvent(
            data=candidate.raw_text,
            reason=reason,
            syntax=_get_syntax_name(candidate.syntax),
            start_line=candidate.start_line,
            end_line=self._line_counter,
            exception=exception,
        )

    async def _flush_candidates(self) -> AsyncGenerator[StreamEvent[BaseMetadata, BaseContent]]:
        """Flush remaining candidates as rejected.

        Yields:
            Rejection events for remaining candidates
        """
        for candidate in self._candidates:
            yield self._create_rejection_event(
                candidate,
                "Stream ended without closing marker",
            )
        self._candidates.clear()
