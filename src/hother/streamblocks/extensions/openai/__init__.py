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

from typing import TYPE_CHECKING, Any

from hother.streamblocks.adapters.categories import EventCategory
from hother.streamblocks.adapters.detection import InputAdapterRegistry

if TYPE_CHECKING:
    from hother.streamblocks.core.protocol_processor import ProtocolStreamProcessor
    from hother.streamblocks.core.registry import Registry
    from hother.streamblocks.core.types import BaseContent, BaseMetadata, StreamEvent


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

    def categorize(self, event: Any) -> EventCategory:
        """Categorize event - all OpenAI chunks are text content.

        Args:
            event: OpenAI ChatCompletionChunk

        Returns:
            TEXT_CONTENT for all chunks
        """
        return EventCategory.TEXT_CONTENT

    def extract_text(self, event: Any) -> str | None:
        """Extract text from choices[0].delta.content.

        Args:
            event: OpenAI ChatCompletionChunk

        Returns:
            Delta content text, or None if not present
        """
        try:
            if hasattr(event, "choices") and len(event.choices) > 0:
                delta = event.choices[0].delta
                return getattr(delta, "content", None)
        except (AttributeError, IndexError):
            pass
        return None

    def is_complete(self, event: Any) -> bool:
        """Check if finish_reason is set.

        Args:
            event: OpenAI ChatCompletionChunk

        Returns:
            True if this is the final chunk
        """
        try:
            if hasattr(event, "choices") and len(event.choices) > 0:
                return event.choices[0].finish_reason is not None
        except (AttributeError, IndexError):
            pass
        return False

    def get_metadata(self, event: Any) -> dict[str, Any] | None:
        """Extract model and finish reason.

        Args:
            event: OpenAI ChatCompletionChunk

        Returns:
            Dictionary with model and/or finish_reason if present
        """
        metadata: dict[str, Any] = {}

        # Extract model name
        if hasattr(event, "model"):
            metadata["model"] = event.model

        # Extract finish reason if present
        try:
            if hasattr(event, "choices") and len(event.choices) > 0:
                choice = event.choices[0]
                if choice.finish_reason:
                    metadata["finish_reason"] = choice.finish_reason
        except (AttributeError, IndexError):
            pass

        return metadata if metadata else None


# Register additional module paths for OpenAI
InputAdapterRegistry.register_module("openai.resources", OpenAIInputAdapter)


def create_openai_processor(
    registry: Registry,
) -> ProtocolStreamProcessor[Any, StreamEvent[BaseMetadata, BaseContent]]:
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
