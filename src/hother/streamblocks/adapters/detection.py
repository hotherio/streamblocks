"""Automatic adapter detection for stream chunks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from hother.streamblocks.adapters.providers import (
    AnthropicAdapter,
    AttributeAdapter,
    GeminiAdapter,
    IdentityAdapter,
    OpenAIAdapter,
)

if TYPE_CHECKING:
    from hother.streamblocks.adapters.base import StreamAdapter


class AdapterDetector:
    """Automatically detect the appropriate adapter for a stream chunk.

    Uses a combination of module-based detection and attribute pattern matching
    to identify the stream format and select the correct adapter.

    Example:
        >>> # Auto-detect from first chunk
        >>> adapter = AdapterDetector.detect(gemini_chunk)
        >>> isinstance(adapter, GeminiAdapter)
        True
        >>>
        >>> # Register custom adapter
        >>> AdapterDetector.register_adapter(
        ...     module_prefix="mycompany.ai",
        ...     adapter_class=MyCustomAdapter
        ... )
    """

    # Registry of known chunk types to adapters (module path → Adapter class)
    _type_registry: dict[str, type[StreamAdapter]] = {
        "google.ai.generativelanguage": GeminiAdapter,
        "google.genai": GeminiAdapter,
        "openai.types.chat": OpenAIAdapter,
        "openai.resources": OpenAIAdapter,
        "anthropic.types": AnthropicAdapter,
        "anthropic.lib": AnthropicAdapter,
    }

    # Attribute-based detection patterns (required_attributes → adapter_class)
    _pattern_registry: list[tuple[list[str], type[StreamAdapter]]] = [
        # Gemini-like structure: has text and candidates
        (["text", "candidates"], GeminiAdapter),
        # OpenAI structure: has choices, model, and object
        (["choices", "model", "object"], OpenAIAdapter),
        # Anthropic events: has type and delta
        (["type", "delta"], AnthropicAdapter),
    ]

    @classmethod
    def detect(cls, chunk: Any) -> StreamAdapter | None:
        """Auto-detect adapter from chunk type.

        Detection strategy:
        1. If chunk is a string, use IdentityAdapter
        2. Try module-based detection (match chunk's module path)
        3. Try attribute-based detection (match required attributes)
        4. Fallback to AttributeAdapter if chunk has 'text' or 'content'
        5. Return None if format is completely unknown

        Args:
            chunk: First chunk from stream

        Returns:
            Appropriate adapter instance, or None if unknown format

        Example:
            >>> detector = AdapterDetector()
            >>> adapter = detector.detect(gemini_chunk)
            >>> isinstance(adapter, GeminiAdapter)
            True
        """
        # Check if it's plain text
        if isinstance(chunk, str):
            return IdentityAdapter()

        # Try module-based detection
        chunk_module = type(chunk).__module__
        for module_prefix, adapter_class in cls._type_registry.items():
            if chunk_module.startswith(module_prefix):
                return adapter_class()

        # Try attribute-based detection
        for required_attrs, adapter_class in cls._pattern_registry:
            if all(hasattr(chunk, attr) for attr in required_attrs):
                return adapter_class()

        # Fallback: try to find a 'text' or 'content' attribute
        if hasattr(chunk, "text"):
            return AttributeAdapter("text")
        if hasattr(chunk, "content"):
            return AttributeAdapter("content")

        # Unknown format
        return None

    @classmethod
    def register_adapter(
        cls,
        module_prefix: str | None = None,
        attributes: list[str] | None = None,
        adapter_class: type[StreamAdapter] | None = None,
    ) -> None:
        """Register a custom adapter for auto-detection.

        You can register either by module prefix or by attribute pattern.
        Module-based detection is checked before attribute-based detection.

        Args:
            module_prefix: Python module path to match (e.g., "mycompany.ai")
            attributes: Required attributes to match
            adapter_class: Adapter class to use when matched

        Example:
            >>> # Register by module
            >>> AdapterDetector.register_adapter(
            ...     module_prefix="mycompany.ai",
            ...     adapter_class=MyCustomAdapter
            ... )
            >>>
            >>> # Register by attributes
            >>> AdapterDetector.register_adapter(
            ...     attributes=["custom_field", "data"],
            ...     adapter_class=MyCustomAdapter
            ... )
        """
        if module_prefix and adapter_class:
            cls._type_registry[module_prefix] = adapter_class

        if attributes and adapter_class:
            # Insert at beginning for higher priority
            cls._pattern_registry.insert(0, (attributes, adapter_class))

    @classmethod
    def clear_custom_adapters(cls) -> None:
        """Clear all custom registered adapters (useful for testing).

        This resets the detector to its default state with only built-in adapters.
        """
        # Reset to default built-in adapters only
        cls._type_registry = {
            "google.ai.generativelanguage": GeminiAdapter,
            "google.genai": GeminiAdapter,
            "openai.types.chat": OpenAIAdapter,
            "openai.resources": OpenAIAdapter,
            "anthropic.types": AnthropicAdapter,
            "anthropic.lib": AnthropicAdapter,
        }

        cls._pattern_registry = [
            (["text", "candidates"], GeminiAdapter),
            (["choices", "model", "object"], OpenAIAdapter),
            (["type", "delta"], AnthropicAdapter),
        ]
