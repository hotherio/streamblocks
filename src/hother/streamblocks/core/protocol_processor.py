"""Protocol stream processor for bidirectional adapter support."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from hother.streamblocks.adapters.categories import EventCategory
from hother.streamblocks.adapters.detection import detect_input_adapter
from hother.streamblocks.adapters.output import StreamBlocksOutputAdapter
from hother.streamblocks.core.processor import ProcessorConfig, StreamBlockProcessor

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from hother.streamblocks.adapters.protocols import (
        InputProtocolAdapter,
        OutputProtocolAdapter,
    )
    from hother.streamblocks.core._logger import Logger
    from hother.streamblocks.core.registry import Registry

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


class ProtocolStreamProcessor[TInput, TOutput]:
    """StreamBlocks processor with bidirectional protocol support.

    This processor enables processing of any input stream format and transformation
    to any output format using the adapter pattern.

    The processor supports three usage modes:

    1. **Auto-detect input**: Pass `input_adapter=None` to auto-detect from first event
    2. **Explicit adapters**: Specify both input and output adapters
    3. **Default output**: Pass `output_adapter=None` to emit native StreamBlocks events

    Example:
        >>> from hother.streamblocks import ProtocolStreamProcessor, Registry
        >>> from hother.streamblocks.adapters.input import IdentityInputAdapter
        >>> from hother.streamblocks.adapters.output import StreamBlocksOutputAdapter
        >>>
        >>> # Auto-detect input, native output
        >>> processor = ProtocolStreamProcessor(registry)
        >>>
        >>> # Explicit adapters
        >>> processor = ProtocolStreamProcessor(
        ...     registry,
        ...     input_adapter=IdentityInputAdapter(),
        ...     output_adapter=StreamBlocksOutputAdapter(),
        ... )
        >>>
        >>> # Process stream
        >>> async for event in processor.process_stream(input_stream):
        ...     if isinstance(event, BlockExtractedEvent):
        ...         print(f"Block: {event.block.metadata.id}")
    """

    def __init__(
        self,
        registry: Registry,
        input_adapter: InputProtocolAdapter[TInput] | None = None,
        output_adapter: OutputProtocolAdapter[TOutput] | None = None,
        config: ProcessorConfig | None = None,
        *,
        logger: Logger | None = None,
    ) -> None:
        """Initialize the protocol stream processor.

        Args:
            registry: Registry with syntax and block definitions
            input_adapter: Input adapter for extracting text from events.
                          If None, will auto-detect from first event.
            output_adapter: Output adapter for transforming StreamBlocks events.
                           If None, will emit native StreamBlocks events.
            config: Configuration object for processor settings
            logger: Optional logger
        """
        self.registry = registry
        self._input_adapter = input_adapter
        self._output_adapter: OutputProtocolAdapter[TOutput] = (
            output_adapter if output_adapter is not None else StreamBlocksOutputAdapter()  # type: ignore[assignment]
        )
        self._auto_detected = False

        # Store config, using modified defaults for protocol processing
        self._config = config or ProcessorConfig(
            emit_original_events=False,  # We handle original events via passthrough
            auto_detect_adapter=False,  # We handle detection ourselves
        )

        # Create internal core processor
        self._core_processor = StreamBlockProcessor(
            registry,
            config=self._config,
            logger=logger,
        )

    @property
    def was_auto_detected(self) -> bool:
        """Whether the input adapter was auto-detected.

        Returns:
            True if adapter was detected from first event, False if explicitly provided
        """
        return self._auto_detected

    @property
    def input_adapter(self) -> InputProtocolAdapter[TInput] | None:
        """The active input adapter (may be auto-detected).

        Returns:
            The input adapter, or None if not yet detected
        """
        return self._input_adapter

    @property
    def output_adapter(self) -> OutputProtocolAdapter[TOutput]:
        """The active output adapter.

        Returns:
            The output adapter
        """
        return self._output_adapter

    async def process_stream(
        self,
        input_stream: AsyncIterator[TInput],
    ) -> AsyncIterator[TOutput]:
        """Process input stream through StreamBlocks, emit output protocol events.

        This method:
        1. Auto-detects input adapter on first event if not specified
        2. Categorizes each event (TEXT_CONTENT, PASSTHROUGH, SKIP)
        3. For TEXT_CONTENT: extracts text, processes through StreamBlocks, transforms output
        4. For PASSTHROUGH: passes event through output adapter's passthrough method
        5. For SKIP: doesn't emit anything

        Args:
            input_stream: Async iterator yielding input events

        Yields:
            Output protocol events

        Example:
            >>> async for event in processor.process_stream(openai_stream):
            ...     if isinstance(event, BlockExtractedEvent):
            ...         print(f"Block: {event.block.metadata.id}")
        """
        async for input_event in input_stream:
            async for output_event in self._process_input_event(input_event):
                yield output_event

        # Finalize stream processing
        async for output_event in self._finalize_stream():
            yield output_event

    async def _process_input_event(
        self,
        input_event: TInput,
    ) -> AsyncIterator[TOutput]:
        """Process a single input event and yield output events."""
        # Auto-detect input adapter on first event if not specified
        if self._input_adapter is None:
            self._input_adapter = detect_input_adapter(input_event)
            self._auto_detected = True

        category = self._input_adapter.categorize(input_event)

        if category == EventCategory.TEXT_CONTENT:
            async for event in self._process_text_content(input_event):
                yield event
        elif category == EventCategory.PASSTHROUGH:
            output = self._output_adapter.passthrough(input_event)
            if output is not None:
                yield output
        # SKIP category: Don't emit anything

    async def _process_text_content(
        self,
        input_event: TInput,
    ) -> AsyncIterator[TOutput]:
        """Process TEXT_CONTENT event and yield output events."""
        # _input_adapter is guaranteed to be set by _process_input_event
        if self._input_adapter is None:  # pragma: no cover
            msg = "Input adapter not initialized - this should not happen"
            raise RuntimeError(msg)
        text = self._input_adapter.extract_text(input_event)
        if text:
            for sb_event in self._core_processor.process_chunk(text):
                async for event in self._transform_sb_event(sb_event):
                    yield event

    async def _transform_sb_event(
        self,
        sb_event: str | object,
    ) -> AsyncIterator[TOutput]:
        """Transform StreamBlocks event to output protocol events."""
        output = self._output_adapter.to_protocol_event(sb_event)  # type: ignore[arg-type]
        if output is not None:
            async for event in self._ensure_async_iterable(output):
                yield event

    async def _finalize_stream(self) -> AsyncIterator[TOutput]:
        """Finalize stream and yield remaining output events."""
        for sb_event in self._core_processor.finalize():
            async for event in self._transform_sb_event(sb_event):
                yield event

    def process_chunk(
        self,
        input_event: TInput,
    ) -> list[TOutput]:
        """Process a single input event synchronously.

        This method is stateful - it maintains internal state between calls.
        Call finalize() after processing all events to flush incomplete blocks.

        Args:
            input_event: Single input event to process

        Returns:
            List of output events generated from this input event
        """
        events: list[TOutput] = []

        # Auto-detect input adapter on first event if not specified
        if self._input_adapter is None:
            self._input_adapter = detect_input_adapter(input_event)
            self._auto_detected = True

        # Categorize the event
        category = self._input_adapter.categorize(input_event)

        if category == EventCategory.TEXT_CONTENT:
            # Extract text and process through StreamBlocks
            text = self._input_adapter.extract_text(input_event)
            if text:
                # Process text chunk and get StreamBlocks events
                for sb_event in self._core_processor.process_chunk(text):
                    output = self._output_adapter.to_protocol_event(sb_event)
                    if output is not None:
                        events.extend(self._ensure_list(output))

        elif category == EventCategory.PASSTHROUGH:
            # Pass through to output adapter
            output = self._output_adapter.passthrough(input_event)
            if output is not None:
                events.append(output)

        # SKIP category: Don't emit anything

        return events

    def finalize(self) -> list[TOutput]:
        """Finalize processing and flush any incomplete blocks.

        Call this method after processing all events to get rejection events
        for any blocks that were opened but never closed.

        Returns:
            List of output events including rejection events for incomplete blocks
        """
        events: list[TOutput] = []

        for sb_event in self._core_processor.finalize():
            output = self._output_adapter.to_protocol_event(sb_event)
            if output is not None:
                events.extend(self._ensure_list(output))

        return events

    def reset(self) -> None:
        """Reset the processor state for reuse.

        This clears all internal state including:
        - Auto-detected adapter (will re-detect on next stream)
        - Core processor buffers and candidates
        """
        self._input_adapter = None
        self._auto_detected = False
        # Recreate core processor to reset its state
        self._core_processor = StreamBlockProcessor(
            self.registry,
            config=self._config,
            logger=self._core_processor.logger,
        )

    async def _ensure_async_iterable(
        self,
        output: TOutput | list[TOutput],
    ) -> AsyncIterator[TOutput]:
        """Ensure output is iterable, yielding single or multiple events.

        Args:
            output: Single event or list of events

        Yields:
            Individual events
        """
        if isinstance(output, list):
            for item in output:
                yield item
        else:
            yield output

    def _ensure_list(self, output: TOutput | list[TOutput]) -> list[TOutput]:
        """Ensure output is a list.

        Args:
            output: Single event or list of events

        Returns:
            List of events
        """
        if isinstance(output, list):
            return output
        return [output]
