"""OpenAI extension for StreamBlocks.

This extension provides input adapters for OpenAI ChatCompletionChunk streams.

Importing this module registers the OpenAIInputAdapter for auto-detection.

Example:
    >>> # Import to enable auto-detection
    >>> import hother.streamblocks.extensions.openai
    >>>
    >>> # Auto-detect from OpenAI stream
    >>> processor = ProtocolStreamProcessor(registry)
    >>> async for event in processor.process_stream(openai_stream):
    ...     print(event)
    >>>
    >>> # Or use convenience factory
    >>> from hother.streamblocks.extensions.openai import create_openai_processor
    >>> processor = create_openai_processor(registry)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from hother.streamblocks.adapters.categories import EventCategory
from hother.streamblocks.adapters.detection import InputAdapterRegistry

# Import OpenAI types - required for this extension
try:
    from openai.types.chat import ChatCompletionChunk
except ImportError as _import_error:
    _msg = 'Please install `openai` to use the OpenAI adapter, you can use the `openai` optional group — `pip install "streamblocks[openai]"`'
    raise ImportError(_msg) from _import_error

if TYPE_CHECKING:
    from hother.streamblocks.core.protocol_processor import ProtocolStreamProcessor
    from hother.streamblocks.core.registry import Registry
    from hother.streamblocks.core.types import BaseEvent


@InputAdapterRegistry.register(module_prefix="openai.types")
class OpenAIInputAdapter:
    """Input adapter for OpenAI ChatCompletionChunk streams.

    Handles streams from openai.AsyncStream[ChatCompletionChunk].

    Extracts:
    - Delta content from choices[0].delta.content
    - Finish reasons
    - Model information

    Example:
        >>> from openai import AsyncOpenAI
        >>> adapter = OpenAIInputAdapter()
        >>>
        >>> client = AsyncOpenAI()
        >>> stream = await client.chat.completions.create(
        ...     model="gpt-4",
        ...     messages=[...],
        ...     stream=True
        ... )
        >>>
        >>> async for chunk in stream:
        ...     text = adapter.extract_text(chunk)
        ...     if adapter.is_complete(chunk):
        ...         print("Stream complete!")
    """

    native_module_prefix: ClassVar[str] = "openai.types"

    def categorize(self, event: ChatCompletionChunk) -> EventCategory:
        """Categorize event - all OpenAI chunks are text content.

        Args:
            event: OpenAI ChatCompletionChunk

        Returns:
            TEXT_CONTENT for all chunks
        """
        return EventCategory.TEXT_CONTENT

    def extract_text(self, event: ChatCompletionChunk) -> str | None:
        """Extract text from choices[0].delta.content.

        Args:
            event: OpenAI ChatCompletionChunk

        Returns:
            Delta content text, or None if not present
        """
        if event.choices:
            delta = event.choices[0].delta
            return delta.content if delta else None
        return None

    def is_complete(self, event: ChatCompletionChunk) -> bool:
        """Check if finish_reason is set.

        Args:
            event: OpenAI ChatCompletionChunk

        Returns:
            True if this is the final chunk
        """
        if event.choices:
            return event.choices[0].finish_reason is not None
        return False

    def get_metadata(self, event: ChatCompletionChunk) -> dict[str, Any] | None:
        """Extract model and finish reason.

        Args:
            event: OpenAI ChatCompletionChunk

        Returns:
            Dictionary with model and/or finish_reason if present
        """
        metadata: dict[str, Any] = {}

        # Extract model name
        if event.model:
            metadata["model"] = event.model

        # Extract finish reason if present
        if event.choices:
            choice = event.choices[0]
            if choice.finish_reason:
                metadata["finish_reason"] = choice.finish_reason

        return metadata if metadata else None


# Register additional module paths for OpenAI
InputAdapterRegistry.register_module("openai.resources", OpenAIInputAdapter)


def create_openai_processor(
    registry: Registry,
) -> ProtocolStreamProcessor[Any, BaseEvent]:
    """Create processor pre-configured for OpenAI streams.

    This is a convenience factory that creates a ProtocolStreamProcessor
    with OpenAIInputAdapter and StreamBlocksOutputAdapter.

    Args:
        registry: Registry with syntax and block definitions

    Returns:
        Pre-configured processor for OpenAI streams

    Example:
        >>> from hother.streamblocks.extensions.openai import create_openai_processor
        >>> processor = create_openai_processor(registry)
        >>> async for event in processor.process_stream(openai_stream):
        ...     if isinstance(event, BlockExtractedEvent):
        ...         print(f"Block: {event.block.metadata.id}")
    """
    from hother.streamblocks.adapters.output import StreamBlocksOutputAdapter
    from hother.streamblocks.core.protocol_processor import ProtocolStreamProcessor

    return ProtocolStreamProcessor(
        registry,
        input_adapter=OpenAIInputAdapter(),
        output_adapter=StreamBlocksOutputAdapter(),
    )


__all__ = [
    "OpenAIInputAdapter",
    "create_openai_processor",
]
