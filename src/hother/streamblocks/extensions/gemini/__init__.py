"""Gemini extension for StreamBlocks.

This extension provides input adapters for Google GenAI streams.

Importing this module registers the GeminiInputAdapter for auto-detection.

Example:
    >>> # Import to enable auto-detection
    >>> import hother.streamblocks.extensions.gemini
    >>>
    >>> # Auto-detect from Gemini stream
    >>> processor = ProtocolStreamProcessor(registry)
    >>> async for event in processor.process_stream(gemini_stream):
    ...     print(event)
    >>>
    >>> # Or use convenience factory
    >>> from hother.streamblocks.extensions.gemini import create_gemini_processor
    >>> processor = create_gemini_processor(registry)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from hother.streamblocks.adapters.categories import EventCategory
from hother.streamblocks.adapters.detection import InputAdapterRegistry

if TYPE_CHECKING:
    from hother.streamblocks.core.protocol_processor import ProtocolStreamProcessor
    from hother.streamblocks.core.registry import Registry
    from hother.streamblocks.core.types import BaseContent, BaseMetadata, StreamEvent


@InputAdapterRegistry.register(
    module_prefix="google.genai",
    attributes=["text", "candidates"],  # Fallback attribute detection
)
class GeminiInputAdapter:
    """Input adapter for Google GenAI streams.

    Handles chunks from google.genai.models.generate_content_stream()
    and google.ai.generativelanguage clients.

    Extracts:
    - Text from chunk.text attribute
    - Usage metadata (token counts)
    - Model version information

    Example:
        >>> from google import genai
        >>> adapter = GeminiInputAdapter()
        >>>
        >>> async for chunk in client.aio.models.generate_content_stream(...):
        ...     text = adapter.extract_text(chunk)
        ...     metadata = adapter.get_metadata(chunk)
        ...     if metadata:
        ...         print(f"Tokens: {metadata['usage']}")
    """

    def categorize(self, event: Any) -> EventCategory:
        """Categorize event - all Gemini chunks are text content.

        Args:
            event: Gemini GenerateContentResponse chunk

        Returns:
            TEXT_CONTENT for all chunks
        """
        return EventCategory.TEXT_CONTENT

    def extract_text(self, event: Any) -> str | None:
        """Extract text from chunk.text attribute.

        Args:
            event: Gemini GenerateContentResponse chunk

        Returns:
            Text content, or None if not present
        """
        return getattr(event, "text", None)

    def is_complete(self, event: Any) -> bool:
        """Gemini doesn't have explicit finish markers in each chunk.

        Completion is typically detected by the stream ending.

        Args:
            event: Gemini GenerateContentResponse chunk

        Returns:
            Always False - Gemini streams end naturally
        """
        return False

    def get_metadata(self, event: Any) -> dict[str, Any] | None:
        """Extract usage metadata and model information.

        Args:
            event: Gemini GenerateContentResponse chunk

        Returns:
            Dictionary with usage and/or model if present
        """
        metadata: dict[str, Any] = {}

        # Extract usage metadata if available
        if hasattr(event, "usage_metadata"):
            metadata["usage"] = event.usage_metadata

        # Extract model version
        if hasattr(event, "model_version"):
            metadata["model"] = event.model_version

        return metadata if metadata else None


# Register additional module paths for Gemini
InputAdapterRegistry.register_module("google.ai.generativelanguage", GeminiInputAdapter)


def create_gemini_processor(
    registry: Registry,
) -> ProtocolStreamProcessor[Any, StreamEvent[BaseMetadata, BaseContent]]:
    """Create processor pre-configured for Gemini streams.

    This is a convenience factory that creates a ProtocolStreamProcessor
    with GeminiInputAdapter and StreamBlocksOutputAdapter.

    Args:
        registry: Registry with syntax and block definitions

    Returns:
        Pre-configured processor for Gemini streams

    Example:
        >>> from hother.streamblocks.extensions.gemini import create_gemini_processor
        >>> processor = create_gemini_processor(registry)
        >>> async for event in processor.process_stream(gemini_stream):
        ...     if isinstance(event, BlockExtractedEvent):
        ...         print(f"Block: {event.block.metadata.id}")
    """
    from hother.streamblocks.adapters.output import StreamBlocksOutputAdapter
    from hother.streamblocks.core.protocol_processor import ProtocolStreamProcessor

    return ProtocolStreamProcessor(
        registry,
        input_adapter=GeminiInputAdapter(),
        output_adapter=StreamBlocksOutputAdapter(),
    )


__all__ = [
    "GeminiInputAdapter",
    "create_gemini_processor",
]
