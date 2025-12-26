"""Stream processing engine for StreamBlocks."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeVar
from uuid import uuid4

from hother.streamblocks.adapters.detection import InputAdapterRegistry
from hother.streamblocks.adapters.input import IdentityInputAdapter
from hother.streamblocks.adapters.protocols import HasNativeModulePrefix
from hother.streamblocks.core._logger import StdlibLoggerAdapter
from hother.streamblocks.core.block_state_machine import BlockStateMachine
from hother.streamblocks.core.constants import LIMITS
from hother.streamblocks.core.line_accumulator import LineAccumulator
from hother.streamblocks.core.types import (
    BlockContentDeltaEvent,
    BlockContentEndEvent,
    BlockEndEvent,
    BlockErrorEvent,
    BlockHeaderDeltaEvent,
    BlockMetadataDeltaEvent,
    BlockMetadataEndEvent,
    BlockStartEvent,
    Event,
    StreamFinishedEvent,
    StreamStartedEvent,
    TextContentEvent,
    TextDeltaEvent,
)
from hother.streamblocks.core.utils import get_syntax_name


@dataclass
class StreamState:
    """Tracks state during stream processing."""

    stream_id: str = field(default_factory=lambda: str(uuid4()))
    start_time: int = field(default_factory=lambda: int(time.time() * 1000))
    blocks_extracted: int = 0
    blocks_rejected: int = 0
    total_events: int = 0

    def duration_ms(self) -> int:
        """Get duration in milliseconds since stream started."""
        return int(time.time() * 1000) - self.start_time


@dataclass(frozen=True, slots=True)
class ProcessorConfig:
    """Configuration for StreamBlockProcessor.

    Attributes:
        lines_buffer: Number of recent lines to keep in buffer for context (default: 5).
            Used for debugging and error messages.
        max_line_length: Maximum line length in bytes before truncation (default: 16,384).
            Lines exceeding this limit are truncated to prevent memory issues.
        max_block_size: Maximum block size in bytes before rejection (default: 1,048,576 = 1MB).
            Blocks exceeding this limit are rejected with SIZE_EXCEEDED error.
        emit_original_events: Whether to pass through original provider events (default: True).
            When False, only StreamBlocks events are emitted. Set to False when using
            IdentityInputAdapter to avoid duplicate events.
        emit_text_deltas: Whether to emit TextDeltaEvent for real-time streaming (default: True).
            Enables character-level streaming for live UIs. Disable to reduce event volume.
        emit_section_end_events: Whether to emit section end events (default: True).
            Controls BlockMetadataEndEvent and BlockContentEndEvent emission for early validation.
        auto_detect_adapter: Whether to auto-detect input adapter from first chunk (default: True).
            When False, uses IdentityInputAdapter. Disable for performance with known adapter.

    Example:
        >>> # Custom configuration for large blocks
        >>> config = ProcessorConfig(
        ...     max_block_size=2_097_152,  # 2MB
        ...     emit_original_events=False,
        ...     emit_text_deltas=False,
        ... )
        >>> processor = StreamBlockProcessor(registry, config=config)
        >>>
        >>> # Minimal configuration for performance
        >>> config = ProcessorConfig(
        ...     emit_section_end_events=False,
        ...     auto_detect_adapter=False,
        ... )
    """

    lines_buffer: int = LIMITS.LINES_BUFFER
    max_line_length: int = LIMITS.MAX_LINE_LENGTH
    max_block_size: int = LIMITS.MAX_BLOCK_SIZE
    emit_original_events: bool = True
    emit_text_deltas: bool = True
    emit_section_end_events: bool = True
    auto_detect_adapter: bool = True


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator, Callable

    from hother.streamblocks.adapters.protocols import InputProtocolAdapter
    from hother.streamblocks.core._logger import Logger
    from hother.streamblocks.core.registry import Registry

# Type variable for chunk types
TChunk = TypeVar("TChunk")


class StreamBlockProcessor:
    """Main stream processing engine for a single syntax type.

    This processor works with exactly one syntax and coordinates:
    - Adapter detection and text extraction
    - Line accumulation via LineAccumulator
    - Block detection and extraction via BlockStateMachine
    - Event emission (TextDeltaEvent, block events, etc.)
    """

    def __init__(
        self,
        registry: Registry,
        config: ProcessorConfig | None = None,
        *,
        logger: Logger | None = None,
        state_machine_factory: Callable[..., BlockStateMachine] = BlockStateMachine,
        accumulator_factory: Callable[..., LineAccumulator] = LineAccumulator,
    ) -> None:
        """Initialize the stream processor.

        Args:
            registry: Registry with a single syntax
            config: Configuration object for processor settings
            logger: Optional logger (any object with debug/info/warning/error/exception methods).
                   Defaults to stdlib logging.getLogger(__name__)
            state_machine_factory: Factory for creating BlockStateMachine (dependency injection)
            accumulator_factory: Factory for creating LineAccumulator (dependency injection)
        """
        self.registry = registry
        self.syntax = registry.syntax
        self.logger = logger or StdlibLoggerAdapter(logging.getLogger(__name__))
        self.config = config or ProcessorConfig()

        # Processing components
        self._line_accumulator = accumulator_factory(
            max_line_length=self.config.max_line_length,
            buffer_size=self.config.lines_buffer,
        )
        self._block_machine = state_machine_factory(
            syntax=self.syntax,
            registry=registry,
            max_block_size=self.config.max_block_size,
            emit_section_end_events=self.config.emit_section_end_events,
            logger=self.logger,
        )
        self._stream_state = StreamState()

        # Adapter state
        self._adapter: InputProtocolAdapter[Any] | None = None
        self._first_chunk_processed = False

    def process_chunk(
        self,
        chunk: TChunk,
        adapter: InputProtocolAdapter[TChunk] | None = None,
    ) -> list[TChunk | Event]:
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

        Raises:
            RuntimeError: If adapter is not set after first chunk processing
                (internal state error, should not occur in normal usage).

        Example:
            >>> processor = StreamBlockProcessor(registry)
            >>> response = await client.generate_content_stream(...)
            >>> async for chunk in response:
            ...     events = processor.process_chunk(chunk)
            ...     for event in events:
            ...         if isinstance(event, BlockEndEvent):
            ...             print(f"Block: {event.block_id}")
            ...
            >>> # Finalize at stream end
            >>> final_events = processor.finalize()
            >>> for event in final_events:
            ...     if isinstance(event, BlockErrorEvent):
            ...         print(f"Incomplete block: {event.reason}")
        """
        events: list[TChunk | Event] = []

        # Auto-detect adapter on first chunk
        self._ensure_adapter(chunk, adapter)

        # Emit original chunk (passthrough)
        if self.config.emit_original_events and not isinstance(self._adapter, IdentityInputAdapter):
            events.append(chunk)

        # Extract text from chunk
        if self._adapter is None:
            msg = "Adapter should be set after first chunk processing"
            raise RuntimeError(msg)
        text = self._adapter.extract_text(chunk)  # type: ignore[arg-type]

        if not text:
            return events

        # Log stream processing start on first chunk with text
        if self._line_accumulator.line_number == 0 and not self._line_accumulator.has_pending_text:
            self.logger.debug(
                "stream_processing_started",
                syntax=get_syntax_name(self.syntax),
                lines_buffer=self.config.lines_buffer,
                max_block_size=self.config.max_block_size,
            )

        # Emit text delta for real-time streaming
        if self.config.emit_text_deltas:
            events.append(self._create_text_delta_event(text))

        # Process text through line accumulator and block state machine
        for line_number, line in self._line_accumulator.add_text(text):
            line_events = self._block_machine.process_line(line, line_number)
            self._update_stats(line_events)
            events.extend(line_events)

        return events

    def finalize(self) -> list[Event]:
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
            ...     if isinstance(event, BlockErrorEvent):
            ...         print(f"Incomplete block: {event.reason}")
        """
        events: list[Event] = []

        # Process any remaining accumulated text as a final line
        final_line = self._line_accumulator.finalize()
        if final_line:
            line_number, line = final_line
            line_events = self._block_machine.process_line(line, line_number)
            self._update_stats(line_events)
            events.extend(line_events)

        # Flush remaining candidates
        flush_events = self._block_machine.flush(self._line_accumulator.line_number)
        self._update_stats(flush_events)
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
            ...     elif isinstance(event, BlockEndEvent):
            ...         # Handle StreamBlocks event
            ...         print(f"Block: {event.block_id}")
        """
        # Check if it's a known StreamBlocks event
        if isinstance(
            event,
            (
                StreamStartedEvent,
                StreamFinishedEvent,
                TextContentEvent,
                TextDeltaEvent,
                BlockStartEvent,
                BlockHeaderDeltaEvent,
                BlockMetadataDeltaEvent,
                BlockContentDeltaEvent,
                BlockMetadataEndEvent,
                BlockContentEndEvent,
                BlockEndEvent,
                BlockErrorEvent,
            ),
        ):
            return False

        # Check if we have an adapter with a module prefix
        if self._adapter is None:
            return False

        # Use Protocol-based check for native module prefix
        if not isinstance(self._adapter, HasNativeModulePrefix):
            return False

        # Check if event's module matches the adapter's prefix
        return type(event).__module__.startswith(self._adapter.native_module_prefix)

    async def process_stream(
        self,
        stream: AsyncIterator[TChunk],
        adapter: InputProtocolAdapter[TChunk] | None = None,
    ) -> AsyncGenerator[TChunk | Event]:
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
            - TextContentEvent, BlockStartEvent, BlockEndEvent, BlockErrorEvent, and section delta events

        Raises:
            RuntimeError: If adapter is not set after first chunk processing
                (internal state error, should not occur in normal usage).

        Example:
            >>> # Plain text
            >>> async for event in processor.process_stream(text_stream):
            ...     if isinstance(event, BlockEndEvent):
            ...         print(f"Extracted: {event.block_id}")
            >>>
            >>> # With Gemini adapter (auto-detected)
            >>> async for event in processor.process_stream(gemini_stream):
            ...     if hasattr(event, 'usage_metadata'):
            ...         print(f"Tokens: {event.usage_metadata}")
            ...     elif isinstance(event, BlockEndEvent):
            ...         print(f"Extracted: {event.block_id}")
        """
        # Set adapter if provided
        if adapter:
            self._adapter = adapter
            self._first_chunk_processed = True

        async for chunk in stream:
            # Auto-detection on first chunk
            self._ensure_adapter(chunk, None)

            # Emit original chunk (passthrough)
            if self.config.emit_original_events and not isinstance(self._adapter, IdentityInputAdapter):
                yield chunk

            # Extract text from chunk
            if self._adapter is None:
                msg = "Adapter should be set after first chunk processing"
                raise RuntimeError(msg)
            text = self._adapter.extract_text(chunk)  # type: ignore[arg-type]

            if not text:
                continue

            # Log stream processing start on first chunk with text
            if self._line_accumulator.line_number == 0 and not self._line_accumulator.has_pending_text:
                self.logger.debug(
                    "stream_processing_started",
                    syntax=get_syntax_name(self.syntax),
                    lines_buffer=self.config.lines_buffer,
                    max_block_size=self.config.max_block_size,
                )

            # Emit text delta for real-time streaming
            if self.config.emit_text_deltas:
                yield self._create_text_delta_event(text)

            # Process text through line accumulator and block state machine
            for line_number, line in self._line_accumulator.add_text(text):
                for event in self._block_machine.process_line(line, line_number):
                    self._update_stats([event])
                    yield event

        # Process any remaining accumulated text as a final line
        final_line = self._line_accumulator.finalize()
        if final_line:
            line_number, line = final_line
            for event in self._block_machine.process_line(line, line_number):
                self._update_stats([event])
                yield event

        # Flush remaining candidates at stream end
        for event in self._block_machine.flush(self._line_accumulator.line_number):
            self._update_stats([event])
            yield event

    def _ensure_adapter(self, chunk: TChunk, adapter: InputProtocolAdapter[TChunk] | None) -> None:
        """Ensure adapter is set, auto-detecting if needed."""
        if self._first_chunk_processed:
            return

        if adapter:
            self._adapter = adapter
        elif self.config.auto_detect_adapter:
            detected = InputAdapterRegistry.detect(chunk)
            if detected:
                self._adapter = detected
                self.logger.info(
                    "adapter_auto_detected",
                    adapter=type(self._adapter).__name__,
                )
            else:
                self._adapter = IdentityInputAdapter()
                self.logger.debug("using_identity_adapter")
        else:
            self._adapter = IdentityInputAdapter()

        self._first_chunk_processed = True

    def _create_text_delta_event(self, text: str) -> TextDeltaEvent:
        """Create a TextDeltaEvent with current block context."""
        inside_block = self._block_machine.has_active_candidates
        block_section = self._block_machine.get_current_section() if inside_block else None
        block_id = self._block_machine.get_current_block_id() if inside_block else None

        return TextDeltaEvent(
            delta=text,
            inside_block=inside_block,
            block_id=block_id,
            section=block_section,
        )

    def _update_stats(self, events: list[Event]) -> None:
        """Update stream state statistics based on events."""
        for event in events:
            if isinstance(event, BlockEndEvent):
                self._stream_state.blocks_extracted += 1
            elif isinstance(event, BlockErrorEvent):
                self._stream_state.blocks_rejected += 1
