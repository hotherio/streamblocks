"""Stream processing engine for block extraction."""

from __future__ import annotations

from collections import deque
from collections.abc import AsyncGenerator, AsyncIterator
from typing import TYPE_CHECKING

from streamblocks.core.models import Block, BlockCandidate
from streamblocks.core.types import BlockState, EventType, StreamEvent

if TYPE_CHECKING:

    from streamblocks.core.registry import BlockRegistry


class StreamBlockProcessor:
    """Main stream processor that coordinates syntax detection and block extraction.

    This processor handles:
    - Async stream processing with proper line accumulation
    - Multiple concurrent block candidates
    - Event emission for all processing stages
    - Size limit enforcement
    - Graceful error recovery
    """

    def __init__(
        self,
        registry: BlockRegistry,
        lines_buffer: int = 5,
        max_line_length: int = 16_384,
        max_block_size: int = 1_048_576,  # 1MB
    ) -> None:
        """Initialize stream processor.

        Args:
            registry: Block registry with syntax definitions
            lines_buffer: Number of lines to keep in buffer
            max_line_length: Maximum line length before truncation
            max_block_size: Maximum block size in bytes
        """
        self.registry = registry
        self.lines_buffer = lines_buffer
        self.max_line_length = max_line_length
        self.max_block_size = max_block_size
        self._buffer: deque[str] = deque(maxlen=lines_buffer)
        self._candidates: list[BlockCandidate] = []
        self._line_counter = 0
        self._accumulated_text: list[str] = []

    async def process_stream(
        self, stream: AsyncIterator[str]
    ) -> AsyncGenerator[StreamEvent]:
        """Process an async stream of text chunks.

        Args:
            stream: Async iterator yielding text chunks

        Yields:
            StreamEvent: Processing events (RAW_TEXT, BLOCK_DELTA, etc.)
        """
        incomplete_line = ""

        async for chunk in stream:
            # Add chunk to accumulated text
            text_to_process = incomplete_line + chunk

            # Split into lines, keeping the last incomplete line
            lines = text_to_process.splitlines(True)

            # Check if last line is complete
            incomplete_line = lines.pop() if lines and not lines[-1].endswith(("\n", "\r\n", "\r")) else ""

            # Process complete lines
            for line in lines:
                # Remove line ending
                line_content = line.rstrip('\r\n')

                # Enforce max line length
                if len(line_content) > self.max_line_length:
                    line_content = line_content[:self.max_line_length]

                self._line_counter += 1

                # Process the line and yield events
                async for event in self._process_line(line_content):
                    yield event

        # Process any remaining incomplete line
        if incomplete_line:
            self._line_counter += 1
            async for event in self._process_line(incomplete_line):
                yield event

        # Flush remaining candidates
        async for event in self._flush_candidates():
            yield event

    async def _process_line(self, line: str) -> AsyncGenerator[StreamEvent]:
        """Process a single line of text.

        Args:
            line: Line content (without line ending)

        Yields:
            StreamEvent: Processing events
        """
        # Add to buffer
        self._buffer.append(line)

        # Check active candidates first
        handled = False
        candidates_to_remove = []

        for i, candidate in enumerate(self._candidates):
            # Get syntax
            syntax = candidate.syntax

            # Check if this line affects this candidate
            detection = syntax.detect_line(line, candidate)

            if detection.is_closing:
                # Block is complete
                candidate.lines.append(line)
                candidate.state = BlockState.COMPLETED

                # Try to extract the block
                event = await self._try_extract_block(candidate)
                if event:
                    yield event
                else:
                    # Failed to extract, create rejection
                    yield self._create_rejection_event(
                        candidate, "Failed to parse block"
                    )

                candidates_to_remove.append(i)
                handled = True

            elif detection.is_metadata_boundary:
                # Handle metadata boundary
                candidate.lines.append(line)

                # Transition state based on current state
                if candidate.state == BlockState.HEADER_DETECTED:
                    candidate.state = BlockState.ACCUMULATING_METADATA
                elif candidate.state == BlockState.ACCUMULATING_METADATA:
                    candidate.state = BlockState.ACCUMULATING_CONTENT

                handled = True

            elif detection.metadata:
                # Store metadata
                candidate.lines.append(line)
                if candidate.metadata is None:
                    candidate.metadata = {}
                candidate.metadata.update(detection.metadata)
                handled = True

            elif candidate.state in [
                BlockState.HEADER_DETECTED,
                BlockState.ACCUMULATING_METADATA,
                BlockState.ACCUMULATING_CONTENT,
            ]:
                # Regular line for this candidate
                candidate.lines.append(line)

                # Add to appropriate section
                if candidate.state == BlockState.ACCUMULATING_METADATA:
                    candidate.metadata_lines.append(line)
                elif candidate.state == BlockState.ACCUMULATING_CONTENT:
                    candidate.content_lines.append(line)

                # Check size limits
                current_size = sum(len(l) for l in candidate.lines)
                if current_size > self.max_block_size:
                    yield self._create_rejection_event(
                        candidate, f"Block too large (>{self.max_block_size} bytes)"
                    )
                    candidates_to_remove.append(i)
                else:
                    # Emit BLOCK_DELTA event
                    yield StreamEvent(
                        type=EventType.BLOCK_DELTA,
                        content=line,
                        line_number=self._line_counter,
                        metadata={
                            "syntax": syntax.name,
                            "start_line": candidate.start_line,
                            "current_line": self._line_counter,
                            "section": "metadata" if candidate.state == BlockState.ACCUMULATING_METADATA else "content",
                            "partial_block": {
                                "delta": line,
                                "accumulated": "\n".join(candidate.lines),
                            },
                        },
                    )

                handled = True

        # Remove completed/rejected candidates
        for i in reversed(candidates_to_remove):
            self._candidates.pop(i)

        # If not handled by any candidate, check for new blocks
        if not handled:
            # Try each syntax in priority order
            syntaxes = self.registry.get_syntaxes_by_priority()

            for syntax in syntaxes:
                detection = syntax.detect_line(line, None)

                if detection.is_opening:
                    # Create new candidate
                    candidate = BlockCandidate(
                        syntax=syntax,
                        start_line=self._line_counter,
                    )
                    candidate.lines.append(line)
                    candidate.state = BlockState.HEADER_DETECTED

                    # Store inline metadata if any
                    if detection.metadata:
                        candidate.metadata = detection.metadata.copy()

                    self._candidates.append(candidate)
                    handled = True
                    break

        # If still not handled, emit as raw text
        if not handled:
            yield StreamEvent(
                type=EventType.RAW_TEXT,
                content=line,
                line_number=self._line_counter,
                metadata={"line_number": self._line_counter},
            )

    async def _try_extract_block(
        self, candidate: BlockCandidate
    ) -> StreamEvent | None:
        """Try to extract and validate a block from a candidate.

        Args:
            candidate: Block candidate to extract

        Returns:
            StreamEvent: BLOCK_EXTRACTED event or None if extraction failed
        """
        syntax = candidate.syntax

        try:
            # Parse the block
            result = syntax.parse_block(candidate)

            if not result.success:
                return None

            # Validate with syntax
            if not syntax.validate_block(result.metadata, result.content):
                return None

            # Create block instance
            block = Block(
                id=getattr(result.metadata, 'id', None),
                type=getattr(result.metadata, 'type', 'unknown'),
                syntax=syntax.name,
                metadata=result.metadata,
                content=result.content,
                source_location=(candidate.start_line, self._line_counter),
                raw_lines=candidate.lines.copy(),
            )

            # Validate with registry if block type is registered
            if block.type and self.registry.is_block_type_registered(block.type):
                is_valid, error = self.registry.validate_block(block)
                if not is_valid:
                    return None

            # Create extracted event
            return StreamEvent(
                type=EventType.BLOCK_EXTRACTED,
                content="\n".join(candidate.lines),
                line_number=self._line_counter,
                metadata={"extracted_block": block},
            )

        except Exception:
            # Any exception during parsing/validation means extraction failed
            return None

    def _create_rejection_event(
        self, candidate: BlockCandidate, reason: str = "Validation failed"
    ) -> StreamEvent:
        """Create a BLOCK_REJECTED event.

        Args:
            candidate: Rejected candidate
            reason: Rejection reason

        Returns:
            StreamEvent: Rejection event
        """
        return StreamEvent(
            type=EventType.BLOCK_REJECTED,
            content="\n".join(candidate.lines),
            line_number=self._line_counter,
            metadata={
                "reason": reason,
                "syntax": candidate.syntax.name,
                "lines": (candidate.start_line, self._line_counter),
            },
        )

    async def _flush_candidates(self) -> AsyncGenerator[StreamEvent]:
        """Flush all remaining candidates as rejected.

        Yields:
            StreamEvent: Rejection events for remaining candidates
        """
        for candidate in self._candidates:
            yield self._create_rejection_event(
                candidate, "Stream ended without closing marker"
            )
        self._candidates.clear()
