"""Stream processing engine for StreamBlocks."""

from __future__ import annotations

import logging
from collections import deque
from typing import TYPE_CHECKING, Any, TypeVar

from hother.streamblocks.adapters.detection import InputAdapterRegistry
from hother.streamblocks.adapters.input import IdentityInputAdapter
from hother.streamblocks.core._logger import StdlibLoggerAdapter
from hother.streamblocks.core.models import BlockCandidate, ExtractedBlock
from hother.streamblocks.core.types import (
    BaseContent,
    BaseMetadata,
    BlockDeltaEvent,
    BlockExtractedEvent,
    BlockOpenedEvent,
    BlockRejectedEvent,
    BlockState,
    RawTextEvent,
    StreamEvent,
    TextDeltaEvent,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator

    from hother.streamblocks.adapters.protocols import InputProtocolAdapter
    from hother.streamblocks.core._logger import Logger
    from hother.streamblocks.core.registry import Registry

# Type variable for chunk types
TChunk = TypeVar("TChunk")


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
        *,
        logger: Logger | None = None,
        lines_buffer: int = 5,
        max_line_length: int = 16_384,
        max_block_size: int = 1_048_576,  # 1MB
        emit_original_events: bool = True,
        emit_text_deltas: bool = True,
        auto_detect_adapter: bool = True,
    ) -> None:
        """Initialize the stream processor.

        Args:
            registry: Registry with a single syntax
            logger: Optional logger (any object with debug/info/warning/error/exception methods).
                   Defaults to stdlib logging.getLogger(__name__)
            lines_buffer: Number of lines to keep in buffer
            max_line_length: Maximum line length before truncation
            max_block_size: Maximum block size in bytes
            emit_original_events: If True, pass through original stream chunks unchanged
            emit_text_deltas: If True, emit TextDeltaEvent for real-time streaming
            auto_detect_adapter: If True, automatically detect adapter from first chunk
        """
        self.registry = registry
        self.syntax = registry.syntax  # Direct access to the syntax
        self.logger = logger or StdlibLoggerAdapter(logging.getLogger(__name__))
        self.lines_buffer = lines_buffer
        self.max_line_length = max_line_length
        self.max_block_size = max_block_size

        # Adapter configuration
        self.emit_original_events = emit_original_events
        self.emit_text_deltas = emit_text_deltas
        self.auto_detect_adapter = auto_detect_adapter

        # Processing state
        self._buffer: deque[str] = deque(maxlen=lines_buffer)
        self._candidates: list[BlockCandidate] = []
        self._line_counter = 0
        self._accumulated_text: list[str] = []

        # Adapter state (for process_chunk)
        self._adapter: InputProtocolAdapter[Any] | None = None
        self._first_chunk_processed = False

    def process_chunk(
        self,
        chunk: TChunk,
        adapter: InputProtocolAdapter[TChunk] | None = None,
    ) -> list[TChunk | StreamEvent[BaseMetadata, BaseContent]]:
        """Process a single chunk and return resulting events.

        This method is stateful - it maintains internal state between calls.
        Call finalize() after processing all chunks to flush incomplete blocks.

        Args:
            chunk: Single chunk to process
            adapter: Optional adapter for extracting text. If not provided and
                    auto_detect_adapter=True, will auto-detect on first chunk.

        Returns:
            List of events generated from this chunk. May be empty if chunk only
            accumulates text without completing any lines.

        Example:
            >>> processor = StreamBlockProcessor(registry)
            >>> response = await client.generate_content_stream(...)
            >>> async for chunk in response:
            ...     events = processor.process_chunk(chunk)
            ...     for event in events:
            ...         if isinstance(event, BlockExtractedEvent):
            ...             print(f"Block: {event.block.metadata.id}")
            ...
            >>> # Finalize at stream end
            >>> final_events = processor.finalize()
            >>> for event in final_events:
            ...     if isinstance(event, BlockRejectedEvent):
            ...         print(f"Incomplete block: {event.reason}")
        """
        events: list[TChunk | StreamEvent[BaseMetadata, BaseContent]] = []

        # Auto-detect adapter on first chunk
        if not self._first_chunk_processed:
            if adapter:
                self._adapter = adapter
            elif self.auto_detect_adapter:
                detected = InputAdapterRegistry.detect(chunk)
                if detected:
                    self._adapter = detected
                    self.logger.info(
                        "adapter_auto_detected",
                        adapter=type(self._adapter).__name__,
                    )
                else:
                    # Assume plain text
                    self._adapter = IdentityInputAdapter()
                    self.logger.debug("using_identity_adapter")
            else:
                self._adapter = IdentityInputAdapter()

            self._first_chunk_processed = True

        # Emit original chunk (passthrough)
        # Only emit for non-text streams to avoid duplication
        if self.emit_original_events and not isinstance(self._adapter, IdentityInputAdapter):
            events.append(chunk)

        # Extract text from chunk
        # At this point, self._adapter is always set (either provided, detected, or IdentityAdapter)
        if self._adapter is None:
            msg = "Adapter should be set after first chunk processing"
            raise RuntimeError(msg)
        text = self._adapter.extract_text(chunk)  # type: ignore[arg-type]  # Contravariance handles any chunk type

        if not text:
            # Chunk had no text, return what we have
            return events

        # Log stream processing start on first chunk with text
        if self._line_counter == 0 and not self._accumulated_text:
            self.logger.debug(
                "stream_processing_started",
                syntax=_get_syntax_name(self.syntax),
                lines_buffer=self.lines_buffer,
                max_block_size=self.max_block_size,
            )

        # Emit text delta for real-time streaming
        if self.emit_text_deltas and text:
            # Check if we're inside a block
            inside_block = len(self._candidates) > 0
            block_section = None
            if inside_block:
                # Get section from first candidate (usually only one)
                block_section = self._candidates[0].current_section

            events.append(
                TextDeltaEvent(
                    data=text,
                    delta=text,
                    inside_block=inside_block,
                    block_section=block_section,
                )
            )

        # Accumulate chunks until we have complete lines
        self._accumulated_text.append(text)

        # Check if we have complete lines
        full_text = "".join(self._accumulated_text)
        lines = full_text.split("\n")

        # Keep incomplete line for next iteration
        if not full_text.endswith("\n"):
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
            line_events = self._process_line_sync(truncated_line)
            events.extend(line_events)

        return events

    def finalize(self) -> list[StreamEvent[BaseMetadata, BaseContent]]:
        """Finalize processing and flush any incomplete blocks.

        Call this method after processing all chunks to get rejection events
        for any blocks that were opened but never closed.

        This method processes any accumulated text as a final line before
        flushing candidates, ensuring the last line is processed even if it
        doesn't end with a newline.

        Returns:
            List of events including processed final line and rejection events
            for incomplete blocks

        Example:
            >>> processor = StreamBlockProcessor(registry)
            >>> async for chunk in stream:
            ...     events = processor.process_chunk(chunk)
            ...     # ... handle events
            ...
            >>> # Stream ended, process remaining text and flush incomplete blocks
            >>> final_events = processor.finalize()
            >>> for event in final_events:
            ...     if isinstance(event, BlockRejectedEvent):
            ...         print(f"Incomplete block: {event.reason}")
        """
        events: list[StreamEvent[BaseMetadata, BaseContent]] = []

        # Process any remaining accumulated text as a final line
        if self._accumulated_text:
            final_line = "".join(self._accumulated_text)
            self._line_counter += 1

            # Enforce max line length
            truncated_line = (
                final_line[: self.max_line_length] if len(final_line) > self.max_line_length else final_line
            )

            # Process final line
            line_events = self._process_line_sync(truncated_line)
            events.extend(line_events)

            # Clear accumulated text
            self._accumulated_text.clear()

        # Now flush any remaining candidates
        flush_events = self._flush_candidates_sync()
        events.extend(flush_events)

        return events

    def is_native_event(self, event: Any) -> bool:
        """Check if event is a native provider event (not a StreamBlocks event).

        This method provides provider-agnostic detection of native events.
        It checks if the event originates from the AI provider (Gemini, OpenAI,
        Anthropic, etc.) versus being a StreamBlocks event.

        Args:
            event: Event to check

        Returns:
            True if event is from the native provider, False if it's a StreamBlocks
            event or if detection is not possible

        Example:
            >>> processor = StreamBlockProcessor(registry)
            >>> async for event in processor.process_stream(gemini_stream):
            ...     if processor.is_native_event(event):
            ...         # Handle Gemini event (provider-agnostic!)
            ...         usage = getattr(event, 'usage_metadata', None)
            ...     elif isinstance(event, BlockExtractedEvent):
            ...         # Handle StreamBlocks event
            ...         print(f"Block: {event.block.metadata.id}")
        """
        # Check if it's a known StreamBlocks event
        if isinstance(
            event,
            (
                RawTextEvent,
                TextDeltaEvent,
                BlockOpenedEvent,
                BlockDeltaEvent,
                BlockExtractedEvent,
                BlockRejectedEvent,
            ),
        ):
            return False

        # Check if we have an adapter with a module prefix
        if self._adapter is None:
            return False

        prefix = getattr(self._adapter, "native_module_prefix", None)
        if prefix is None:
            return False

        # Check if event's module matches the adapter's prefix
        return type(event).__module__.startswith(prefix)

    async def process_stream(
        self,
        stream: AsyncIterator[TChunk],
        adapter: InputProtocolAdapter[TChunk] | None = None,
    ) -> AsyncGenerator[TChunk | StreamEvent[BaseMetadata, BaseContent]]:
        """Process stream and yield mixed events.

        This method processes chunks from any stream format, extracting text
        via an adapter and emitting both original chunks (if enabled) and
        StreamBlocks events.

        Args:
            stream: Async iterator yielding chunks (text or objects)
            adapter: Optional adapter for extracting text from chunks.
                    If None and auto_detect_adapter=True, will auto-detect from first chunk.

        Yields:
            Mixed stream of:
            - Original chunks (if emit_original_events=True)
            - TextDeltaEvent (if emit_text_deltas=True)
            - RawTextEvent, BlockOpenedEvent, BlockDeltaEvent, BlockExtractedEvent, BlockRejectedEvent

        Example:
            >>> # Plain text (backward compatible)
            >>> async for event in processor.process_stream(text_stream):
            ...     if isinstance(event, BlockExtractedEvent):
            ...         print(f"Extracted: {event.block}")
            >>>
            >>> # With Gemini adapter (auto-detected)
            >>> async for event in processor.process_stream(gemini_stream):
            ...     if hasattr(event, 'usage_metadata'):
            ...         print(f"Tokens: {event.usage_metadata}")
            ...     elif isinstance(event, BlockExtractedEvent):
            ...         print(f"Extracted: {event.block}")
        """
        # Set adapter if provided, otherwise will auto-detect
        if adapter:
            self._adapter = adapter
            self._first_chunk_processed = True

        async for chunk in stream:
            # Auto-detection on first chunk
            if not self._first_chunk_processed and self.auto_detect_adapter:
                detected = InputAdapterRegistry.detect(chunk)
                if detected:
                    self._adapter = detected
                    self.logger.info(
                        "adapter_auto_detected",
                        adapter=type(self._adapter).__name__,
                    )
                else:
                    # Assume plain text
                    self._adapter = IdentityInputAdapter()
                    self.logger.debug("using_identity_adapter")

                self._first_chunk_processed = True

            # Emit original chunk (passthrough)
            # Only emit for non-text streams to avoid duplication with plain text
            if self.emit_original_events and not isinstance(self._adapter, IdentityInputAdapter):
                yield chunk

            # Extract text from chunk
            # At this point, self._adapter is always set (either provided, detected, or IdentityAdapter)
            if self._adapter is None:
                msg = "Adapter should be set after first chunk processing"
                raise RuntimeError(msg)
            text = self._adapter.extract_text(chunk)  # type: ignore[arg-type]  # Contravariance handles any chunk type

            if not text:
                # Chunk had no text, continue
                continue

            # Log stream processing start on first chunk with text
            if self._line_counter == 0 and not self._accumulated_text:
                self.logger.debug(
                    "stream_processing_started",
                    syntax=_get_syntax_name(self.syntax),
                    lines_buffer=self.lines_buffer,
                    max_block_size=self.max_block_size,
                )

            # Emit text delta for real-time streaming
            if self.emit_text_deltas and text:
                # Check if we're inside a block
                inside_block = len(self._candidates) > 0
                block_section = None
                if inside_block:
                    # Get section from first candidate (usually only one)
                    block_section = self._candidates[0].current_section

                yield TextDeltaEvent(
                    data=text,
                    delta=text,
                    inside_block=inside_block,
                    block_section=block_section,
                )

            # Accumulate chunks until we have complete lines
            self._accumulated_text.append(text)

            # Check if we have complete lines
            full_text = "".join(self._accumulated_text)
            lines = full_text.split("\n")

            # Keep incomplete line for next iteration
            if not full_text.endswith("\n"):
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

        # Process any remaining accumulated text as a final line
        if self._accumulated_text:
            final_line = "".join(self._accumulated_text)
            self._line_counter += 1

            # Enforce max line length
            truncated_line = (
                final_line[: self.max_line_length] if len(final_line) > self.max_line_length else final_line
            )

            # Process final line
            async for event in self._process_line(truncated_line):
                yield event

            # Clear accumulated text
            self._accumulated_text.clear()

        # Flush remaining candidates at stream end
        async for event in self._flush_candidates():
            yield event

    def _process_line_sync(
        self,
        line: str,
    ) -> list[StreamEvent[BaseMetadata, BaseContent]]:
        """Process a single line through detection (synchronous version).

        Args:
            line: Line to process

        Returns:
            List of StreamEvent objects generated from this line
        """
        events: list[StreamEvent[BaseMetadata, BaseContent]] = []

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
                event = self._try_extract_block(candidate)
                events.append(event)
                self._candidates.remove(candidate)
                handled_by_candidate = True

            elif detection.is_metadata_boundary:
                # Syntax detected a metadata boundary
                candidate.add_line(line)
                # Syntax may update candidate.current_section internally

                # Emit delta event
                events.append(
                    BlockDeltaEvent(
                        data=line,
                        syntax=_get_syntax_name(candidate.syntax),
                        start_line=candidate.start_line,
                        current_line=self._line_counter,
                        section=candidate.current_section,
                        delta=line,
                        accumulated=candidate.raw_text,
                    )
                )
                handled_by_candidate = True

            else:
                # Regular line inside block
                candidate.add_line(line)

                # Check size limit
                if len(candidate.raw_text) > self.max_block_size:
                    events.append(
                        self._create_rejection_event(
                            candidate,
                            "Block size exceeded",
                        )
                    )
                    self._candidates.remove(candidate)
                    handled_by_candidate = True
                    continue

                # The syntax's detect_line may have updated internal state
                # (e.g., added to metadata_lines or content_lines)

                # Emit delta event
                events.append(
                    BlockDeltaEvent(
                        data=line,
                        syntax=_get_syntax_name(candidate.syntax),
                        start_line=candidate.start_line,
                        current_line=self._line_counter,
                        section=candidate.current_section,
                        delta=line,
                        accumulated=candidate.raw_text,
                    )
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

                # Emit BlockOpenedEvent
                events.append(
                    BlockOpenedEvent(
                        data=line,
                        syntax=_get_syntax_name(candidate.syntax),
                        start_line=candidate.start_line,
                        inline_metadata=detection.metadata,
                    )
                )

                self.logger.debug(
                    "block_candidate_created",
                    syntax=_get_syntax_name(candidate.syntax),
                    start_line=candidate.start_line,
                    inline_metadata=bool(detection.metadata),
                )

            # If no candidates and no openings, emit raw text
            if not opening_found:
                events.append(
                    RawTextEvent(
                        data=line,
                        line_number=self._line_counter,
                    )
                )

        return events

    async def _process_line(
        self,
        line: str,
    ) -> AsyncGenerator[StreamEvent[BaseMetadata, BaseContent]]:
        """Process a single line through detection (async wrapper).

        Args:
            line: Line to process

        Yields:
            StreamEvent objects
        """
        events = self._process_line_sync(line)
        for event in events:
            yield event

    def _try_extract_block(
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

        self.logger.debug(
            "extracting_block",
            syntax=_get_syntax_name(candidate.syntax),
            block_type=block_type,
            start_line=candidate.start_line,
            end_line=self._line_counter,
            size_bytes=len(candidate.raw_text),
        )

        # Step 2: Look up block_class from registry
        block_class = None
        if block_type:
            block_class = self.registry.get_block_class(block_type)

        # Step 3: Parse with the appropriate block_class
        parse_result = candidate.syntax.parse_block(candidate, block_class)

        if not parse_result.success:
            error = parse_result.error or "Parse failed"
            self.logger.warning(
                "block_parse_failed",
                block_type=block_type,
                error=error,
                syntax=_get_syntax_name(candidate.syntax),
                exc_info=parse_result.exception,
            )
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
            self.logger.warning(
                "syntax_validation_failed",
                block_type=block_type,
                syntax=block.syntax_name,
            )
            return self._create_rejection_event(candidate, "Syntax validation failed")

        # Registry validation (user-defined validators)
        if not self.registry.validate_block(block):
            self.logger.warning(
                "registry_validation_failed",
                block_type=block_type,
                syntax=block.syntax_name,
            )
            return self._create_rejection_event(candidate, "Registry validation failed")

        self.logger.info(
            "block_extracted",
            block_type=block_type,
            block_id=block.hash_id,
            syntax=block.syntax_name,
            lines=(block.line_start, block.line_end),
            size_bytes=len(block.raw_text),
        )

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
        self.logger.warning(
            "block_rejected",
            reason=reason,
            syntax=_get_syntax_name(candidate.syntax),
            lines=(candidate.start_line, self._line_counter),
            has_exception=exception is not None,
            exc_info=exception if exception else None,
        )

        return BlockRejectedEvent(
            data=candidate.raw_text,
            reason=reason,
            syntax=_get_syntax_name(candidate.syntax),
            start_line=candidate.start_line,
            end_line=self._line_counter,
            exception=exception,
        )

    def _flush_candidates_sync(self) -> list[StreamEvent[BaseMetadata, BaseContent]]:
        """Flush remaining candidates as rejected (synchronous version).

        Returns:
            List of rejection events for remaining candidates
        """
        events: list[StreamEvent[BaseMetadata, BaseContent]] = []
        for candidate in self._candidates:
            events.append(
                self._create_rejection_event(
                    candidate,
                    "Stream ended without closing marker",
                )
            )
        self._candidates.clear()
        return events

    async def _flush_candidates(self) -> AsyncGenerator[StreamEvent[BaseMetadata, BaseContent]]:
        """Flush remaining candidates as rejected (async wrapper).

        Yields:
            Rejection events for remaining candidates
        """
        events = self._flush_candidates_sync()
        for event in events:
            yield event
