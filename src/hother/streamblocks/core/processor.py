"""Stream processing engine for StreamBlocks."""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Any

from hother.streamblocks.core.models import Block, BlockCandidate
from hother.streamblocks.core.types import BlockState, EventType, StreamEvent

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator

    from hother.streamblocks.core.protocols import BlockSyntax
    from hother.streamblocks.core.registry import Registry


class StreamBlockProcessor[TSyntax: "BlockSyntax[Any, Any]"]:
    """Main stream processing engine for a single syntax type.

    This processor works with exactly one syntax type, ensuring type safety
    and simplified processing logic.
    """

    def __init__(
        self,
        registry: Registry[TSyntax],
        lines_buffer: int = 5,
        max_line_length: int = 16_384,
        max_block_size: int = 1_048_576,  # 1MB
    ) -> None:
        """Initialize the stream processor.

        Args:
            registry: Type-specific registry with a single syntax
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
    ) -> AsyncGenerator[StreamEvent[Any, Any]]:
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
    ) -> AsyncGenerator[StreamEvent[Any, Any]]:
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
                if event:
                    yield event
                    self._candidates.remove(candidate)
                    handled_by_candidate = True
                else:
                    # Validation failed, reject
                    yield self._create_rejection_event(candidate, "Validation failed")
                    self._candidates.remove(candidate)
                    handled_by_candidate = True

            elif detection.is_metadata_boundary:
                # Syntax detected a metadata boundary
                candidate.add_line(line)
                # Syntax may update candidate.current_section internally

                # Emit delta event
                yield StreamEvent(
                    type=EventType.BLOCK_DELTA,
                    data=line,
                    content={
                        "syntax": candidate.syntax.name,
                        "start_line": candidate.start_line,
                        "current_line": self._line_counter,
                        "section": candidate.current_section,
                        "partial_block": {
                            "delta": line,
                            "accumulated": candidate.raw_text,
                        },
                    },
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
                yield StreamEvent(
                    type=EventType.BLOCK_DELTA,
                    data=line,
                    content={
                        "syntax": candidate.syntax.name,
                        "start_line": candidate.start_line,
                        "current_line": self._line_counter,
                        "section": candidate.current_section,
                        "partial_block": {
                            "delta": line,
                            "accumulated": candidate.raw_text,
                        },
                    },
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
                yield StreamEvent(
                    type=EventType.RAW_TEXT,
                    data=line,
                    content={"line_number": self._line_counter},
                )

    async def _try_extract_block(
        self,
        candidate: BlockCandidate,
    ) -> StreamEvent[Any, Any] | None:
        """Try to parse and validate a complete block.

        Args:
            candidate: Block candidate to extract

        Returns:
            BLOCK_EXTRACTED event or None if extraction failed
        """
        # Delegate parsing to the syntax
        parse_result = candidate.syntax.parse_block(candidate)

        if not parse_result.success:
            return None

        metadata = parse_result.metadata
        content = parse_result.content

        if metadata is None or content is None:
            return None

        # Additional validation from syntax
        if not candidate.syntax.validate_block(metadata, content):
            return None

        # Registry validation (user-defined validators)
        block_type = getattr(metadata, "block_type", None) or getattr(metadata, "type", None)
        if block_type and not self.registry.validate_block(block_type, metadata, content):
            return None

        # Create block envelope with separate metadata and data
        block = Block(
            metadata=metadata,
            data=content,
            syntax_name=candidate.syntax.name,
            raw_text=candidate.raw_text,
            line_start=candidate.start_line,
            line_end=self._line_counter,
            hash_id=candidate.compute_hash(),
        )

        return StreamEvent(
            type=EventType.BLOCK_EXTRACTED,
            data=candidate.raw_text,
            block=block,
        )

    def _create_rejection_event(
        self,
        candidate: BlockCandidate,
        reason: str = "Validation failed",
    ) -> StreamEvent[Any, Any]:
        """Create a rejection event.

        Args:
            candidate: Rejected candidate
            reason: Reason for rejection

        Returns:
            BLOCK_REJECTED event
        """
        return StreamEvent(
            type=EventType.BLOCK_REJECTED,
            data=candidate.raw_text,
            content={
                "reason": reason,
                "syntax": candidate.syntax.name,
                "lines": (candidate.start_line, self._line_counter),
            },
        )

    async def _flush_candidates(self) -> AsyncGenerator[StreamEvent[Any, Any]]:
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
