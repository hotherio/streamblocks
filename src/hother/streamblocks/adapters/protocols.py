"""Protocol definitions for bidirectional stream adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, TypeVar, runtime_checkable

from hother.streamblocks.adapters.categories import EventCategory  # noqa: TC001 - needed at runtime for Protocol

if TYPE_CHECKING:
    from hother.streamblocks.core.types import BaseEvent

TInput = TypeVar("TInput", contravariant=True)
TOutput = TypeVar("TOutput", covariant=True)


@runtime_checkable
class InputProtocolAdapter(Protocol[TInput]):
    """Protocol for transforming input events for StreamBlocks processing.

    Handles any input format: chunks (OpenAI), events (AG-UI), or custom.

    Example:
        >>> class MyInputAdapter:
        ...     def categorize(self, event: MyEvent) -> EventCategory:
        ...         if event.has_text:
        ...             return EventCategory.TEXT_CONTENT
        ...         return EventCategory.PASSTHROUGH
        ...
        ...     def extract_text(self, event: MyEvent) -> str | None:
        ...         return event.text
    """

    def categorize(self, event: TInput) -> EventCategory:
        """Categorize event for routing.

        Args:
            event: Input event to categorize

        Returns:
            - TEXT_CONTENT: Event contains text, process with StreamBlocks
            - PASSTHROUGH: Pass through to output unchanged
            - SKIP: Don't include in output
        """
        ...

    def extract_text(self, event: TInput) -> str | None:
        """Extract text content from TEXT_CONTENT events.

        Only called for events categorized as TEXT_CONTENT.

        This method can perform any complex extraction/computation:
        - Simple field access: return event.text
        - Nested extraction: return event.data.content.text
        - Multiple fields: return f"{event.prefix}{event.body}"
        - Decoding: return base64.decode(event.encoded_text)
        - JSON extraction: return json.loads(event.payload)["message"]

        Args:
            event: Input event to extract text from

        Returns:
            Extracted text, or None if no text available
        """
        ...

    def get_metadata(self, event: TInput) -> dict[str, Any] | None:
        """Extract protocol-specific metadata from event (optional).

        Args:
            event: Input event to extract metadata from

        Returns:
            Dictionary of metadata, or None
        """
        return None

    def is_complete(self, event: TInput) -> bool:
        """Check if this event signals stream completion (optional).

        Args:
            event: Input event to check

        Returns:
            True if this is the final event in the stream
        """
        return False


@runtime_checkable
class OutputProtocolAdapter(Protocol[TOutput]):
    """Protocol for transforming StreamBlocks events to output format.

    Can emit to any protocol: AG-UI, custom events, plain text, etc.

    Example:
        >>> class MyOutputAdapter:
        ...     def to_protocol_event(self, event: BaseEvent) -> MyEvent | None:
        ...         if isinstance(event, BlockEndEvent):
        ...             return MyEvent(type="block", data=event.get_block())
        ...         return None
        ...
        ...     def passthrough(self, original_event: Any) -> MyEvent | None:
        ...         return MyEvent(type="passthrough", data=original_event)
    """

    def to_protocol_event(
        self,
        event: BaseEvent,
    ) -> TOutput | list[TOutput] | None:
        """Convert a StreamBlocks event to output protocol event(s).

        Args:
            event: StreamBlocks event to convert

        Returns:
            - Single event
            - List of events (for protocols requiring start/content/end pattern)
            - None to skip emission
        """
        ...

    def passthrough(
        self,
        original_event: Any,
    ) -> TOutput | None:
        """Handle passthrough events.

        Called for events categorized as PASSTHROUGH by the input adapter.

        Args:
            original_event: Original input event to pass through

        Returns:
            - The event in output protocol format
            - None if this adapter can't handle the event type
        """
        ...


@runtime_checkable
class HasNativeModulePrefix(Protocol):
    """Protocol for adapters that can identify native events by module prefix.

    Adapters implementing this protocol can help the processor determine
    which events are "native" to their protocol and should be passed through.

    Example:
        >>> class OpenAIInputAdapter:
        ...     native_module_prefix: ClassVar[str] = "openai.types"
        ...     ...
    """

    native_module_prefix: str


@runtime_checkable
class BidirectionalAdapter(Protocol[TInput, TOutput]):
    """Combined bidirectional adapter for full protocol transformation.

    This is a convenience pattern - users can also use separate adapters.

    Example:
        >>> class MyBidirectionalAdapter:
        ...     def __init__(self):
        ...         self._input = MyInputAdapter()
        ...         self._output = MyOutputAdapter()
        ...
        ...     @property
        ...     def input_adapter(self) -> MyInputAdapter:
        ...         return self._input
        ...
        ...     @property
        ...     def output_adapter(self) -> MyOutputAdapter:
        ...         return self._output
    """

    @property
    def input_adapter(self) -> InputProtocolAdapter[TInput]:
        """Input protocol adapter."""
        ...

    @property
    def output_adapter(self) -> OutputProtocolAdapter[TOutput]:
        """Output protocol adapter."""
        ...
