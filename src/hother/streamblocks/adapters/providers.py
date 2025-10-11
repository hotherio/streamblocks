"""Built-in adapters for common AI provider streaming formats."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class IdentityAdapter:
    """Adapter for plain text streams (default behavior).

    This adapter passes through plain text strings unchanged,
    maintaining backward compatibility with existing code.

    Example:
        >>> adapter = IdentityAdapter()
        >>> adapter.extract_text("Hello world")
        "Hello world"
    """

    native_module_prefix: str | None = None

    def extract_text(self, chunk: str) -> str | None:
        """Return text unchanged."""
        return chunk

    def is_complete(self, chunk: str) -> bool:
        """Plain text streams don't have explicit completion markers."""
        return False

    def get_metadata(self, chunk: str) -> dict[str, Any] | None:
        """No metadata for plain text."""
        return None


class AttributeAdapter:
    """Generic adapter for objects with a text attribute.

    Works for any object that has a specified attribute (e.g., chunk.text or chunk.content).
    Automatically detects completion via finish_reason attribute if present.

    Example:
        >>> # For chunks with .text attribute
        >>> adapter = AttributeAdapter("text")
        >>> adapter.extract_text(chunk)
        "Hello world"
        >>>
        >>> # For chunks with .content attribute
        >>> adapter = AttributeAdapter("content")
        >>> adapter.extract_text(chunk)
        "Hello world"
    """

    native_module_prefix: str | None = None

    def __init__(self, text_attr: str = "text") -> None:
        """Initialize attribute adapter.

        Args:
            text_attr: Name of the attribute containing text (default: "text")
        """
        self.text_attr = text_attr

    def extract_text(self, chunk: Any) -> str | None:
        """Extract text from specified attribute."""
        return getattr(chunk, self.text_attr, None)

    def is_complete(self, chunk: Any) -> bool:
        """Check for finish_reason or similar completion marker."""
        return getattr(chunk, "finish_reason", None) is not None

    def get_metadata(self, chunk: Any) -> dict[str, Any] | None:
        """Extract common metadata fields if present."""
        metadata: dict[str, Any] = {}

        # Try to extract finish reason
        if hasattr(chunk, "finish_reason") and chunk.finish_reason:
            metadata["finish_reason"] = chunk.finish_reason

        # Try to extract model
        if hasattr(chunk, "model"):
            metadata["model"] = chunk.model

        return metadata if metadata else None


class GeminiAdapter:
    """Adapter for Google GenAI streams.

    Handles chunks from google.genai.models.generate_content_stream()
    and google.ai.generativelanguage clients.

    Extracts:
    - Text from chunk.text attribute
    - Usage metadata (token counts)
    - Model version information

    Example:
        >>> from google import genai
        >>> adapter = GeminiAdapter()
        >>>
        >>> async for chunk in client.aio.models.generate_content_stream(...):
        ...     text = adapter.extract_text(chunk)
        ...     metadata = adapter.get_metadata(chunk)
        ...     if metadata:
        ...         print(f"Tokens: {metadata['usage']}")
    """

    native_module_prefix = "google.genai."

    def extract_text(self, chunk: Any) -> str | None:
        """Extract from chunk.text attribute."""
        return getattr(chunk, "text", None)

    def is_complete(self, chunk: Any) -> bool:
        """Gemini doesn't have explicit finish markers in each chunk.

        Completion is typically detected by the stream ending.
        """
        return False

    def get_metadata(self, chunk: Any) -> dict[str, Any] | None:
        """Extract usage metadata and model information."""
        metadata: dict[str, Any] = {}

        # Extract usage metadata if available
        if hasattr(chunk, "usage_metadata"):
            metadata["usage"] = chunk.usage_metadata

        # Extract model version
        if hasattr(chunk, "model_version"):
            metadata["model"] = chunk.model_version

        return metadata if metadata else None


class OpenAIAdapter:
    """Adapter for OpenAI ChatCompletionChunk streams.

    Handles streams from openai.AsyncStream[ChatCompletionChunk].

    Extracts:
    - Delta content from choices[0].delta.content
    - Finish reasons
    - Model information

    Example:
        >>> from openai import AsyncOpenAI
        >>> adapter = OpenAIAdapter()
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

    native_module_prefix = "openai."

    def extract_text(self, chunk: Any) -> str | None:
        """Extract from choices[0].delta.content."""
        try:
            if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                return getattr(delta, "content", None)
        except (AttributeError, IndexError):
            pass
        return None

    def is_complete(self, chunk: Any) -> bool:
        """Check if finish_reason is set."""
        try:
            if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                return chunk.choices[0].finish_reason is not None
        except (AttributeError, IndexError):
            pass
        return False

    def get_metadata(self, chunk: Any) -> dict[str, Any] | None:
        """Extract model and finish reason."""
        metadata: dict[str, Any] = {}

        # Extract model name
        if hasattr(chunk, "model"):
            metadata["model"] = chunk.model

        # Extract finish reason if present
        try:
            if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                choice = chunk.choices[0]
                if choice.finish_reason:
                    metadata["finish_reason"] = choice.finish_reason
        except (AttributeError, IndexError):
            pass

        return metadata if metadata else None


class AnthropicAdapter:
    """Adapter for Anthropic message streams.

    Handles event-based streaming from anthropic.MessageStream.

    Anthropic uses different event types:
    - content_block_delta: Contains text deltas
    - message_delta: Contains usage information
    - message_stop: Signals stream completion

    Example:
        >>> from anthropic import AsyncAnthropic
        >>> adapter = AnthropicAdapter()
        >>>
        >>> client = AsyncAnthropic()
        >>> async with client.messages.stream(...) as stream:
        ...     async for event in stream:
        ...         text = adapter.extract_text(event)
        ...         if text:
        ...             print(text, end='', flush=True)
        ...         if adapter.is_complete(event):
        ...             print("\\nDone!")
    """

    native_module_prefix = "anthropic."

    def extract_text(self, chunk: Any) -> str | None:
        """Extract text from content_block_delta events."""
        event_type = getattr(chunk, "type", None)

        if event_type == "content_block_delta":
            delta = getattr(chunk, "delta", None)
            if delta and hasattr(delta, "text"):
                return delta.text

        return None

    def is_complete(self, chunk: Any) -> bool:
        """Check for message_stop event."""
        return getattr(chunk, "type", None) == "message_stop"

    def get_metadata(self, chunk: Any) -> dict[str, Any] | None:
        """Extract stop reason and usage information."""
        event_type = getattr(chunk, "type", None)
        metadata: dict[str, Any] = {}

        if event_type == "message_stop":
            if hasattr(chunk, "stop_reason"):
                metadata["stop_reason"] = chunk.stop_reason
            return metadata if metadata else None

        if event_type == "message_delta":
            if hasattr(chunk, "usage"):
                metadata["usage"] = chunk.usage
            return metadata if metadata else None

        return None


class CallableAdapter:
    """Adapter using user-provided extraction functions.

    For custom stream formats not covered by built-in adapters.
    Allows complete customization of text extraction and metadata handling.

    Example:
        >>> # Simple extraction
        >>> adapter = CallableAdapter(
        ...     extract_fn=lambda chunk: chunk.get("text"),
        ... )
        >>>
        >>> # With completion detection
        >>> adapter = CallableAdapter(
        ...     extract_fn=lambda c: c.get("text"),
        ...     is_complete_fn=lambda c: c.get("done", False),
        ... )
        >>>
        >>> # With metadata extraction
        >>> def get_meta(chunk):
        ...     if "usage" in chunk:
        ...         return {"tokens": chunk["usage"]["total"]}
        ...     return None
        >>>
        >>> adapter = CallableAdapter(
        ...     extract_fn=lambda c: c.get("text"),
        ...     metadata_fn=get_meta,
        ... )
    """

    def __init__(
        self,
        extract_fn: Callable[[Any], str | None],
        is_complete_fn: Callable[[Any], bool] | None = None,
        metadata_fn: Callable[[Any], dict[str, Any] | None] | None = None,
        native_module_prefix: str | None = None,
    ) -> None:
        """Initialize callable adapter.

        Args:
            extract_fn: Function to extract text from chunk
            is_complete_fn: Optional function to check if chunk signals completion
            metadata_fn: Optional function to extract metadata from chunk
            native_module_prefix: Optional module prefix for native event detection
                                 (e.g., "mycompany.ai.")
        """
        self._extract_fn = extract_fn
        self._is_complete_fn: Callable[[Any], bool] = (
            is_complete_fn if is_complete_fn is not None else (lambda _chunk: False)
        )
        self._metadata_fn = metadata_fn
        self.native_module_prefix = native_module_prefix

    def extract_text(self, chunk: Any) -> str | None:
        """Call user-provided extraction function."""
        return self._extract_fn(chunk)

    def is_complete(self, chunk: Any) -> bool:
        """Call user-provided completion check."""
        return self._is_complete_fn(chunk)

    def get_metadata(self, chunk: Any) -> dict[str, Any] | None:
        """Call user-provided metadata extractor if available."""
        if self._metadata_fn:
            return self._metadata_fn(chunk)
        return None
