"""Automatic adapter detection for stream chunks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Callable

    from hother.streamblocks.adapters.protocols import InputProtocolAdapter


@runtime_checkable
class HasText(Protocol):
    """Protocol for objects with a text attribute."""

    text: str | None


@runtime_checkable
class HasContent(Protocol):
    """Protocol for objects with a content attribute."""

    content: str | None


class InputAdapterRegistry:
    """Registry for input adapter auto-detection.

    Uses module prefix matching and attribute-based fallback detection.
    Extensions register themselves when imported.

    Example:
        >>> # Register via decorator
        >>> @InputAdapterRegistry.register(module_prefix="openai.")
        ... class OpenAIInputAdapter:
        ...     def categorize(self, event) -> EventCategory:
        ...         return EventCategory.TEXT_CONTENT
        ...     def extract_text(self, event) -> str | None:
        ...         return event.choices[0].delta.content
        >>>
        >>> # Register via method
        >>> InputAdapterRegistry.register_module("mycompany.api", MyCustomAdapter)
        >>>
        >>> # Detect adapter from sample
        >>> adapter = InputAdapterRegistry.detect(sample_chunk)
    """

    # Module prefix → Adapter class (e.g., "openai." → OpenAIInputAdapter)
    _type_registry: ClassVar[dict[str, type[InputProtocolAdapter[Any]]]] = {}

    # Attribute patterns → Adapter class (for duck-typing detection)
    _pattern_registry: ClassVar[list[tuple[list[str], type[InputProtocolAdapter[Any]]]]] = []

    @classmethod
    def register(
        cls,
        *,
        module_prefix: str | None = None,
        attributes: list[str] | None = None,
    ) -> Callable[[type[InputProtocolAdapter[Any]]], type[InputProtocolAdapter[Any]]]:
        """Decorator to register an adapter for auto-detection.

        Args:
            module_prefix: Module path prefix to match (e.g., "openai.types")
            attributes: Required attributes for attribute-based detection

        Returns:
            Decorator function

        Example:
            >>> @InputAdapterRegistry.register(module_prefix="openai.")
            ... class OpenAIInputAdapter:
            ...     ...
            >>>
            >>> @InputAdapterRegistry.register(attributes=["text", "candidates"])
            ... class GeminiInputAdapter:
            ...     ...
        """

        def decorator(
            adapter_class: type[InputProtocolAdapter[Any]],
        ) -> type[InputProtocolAdapter[Any]]:
            if module_prefix:
                cls._type_registry[module_prefix] = adapter_class
            if attributes:
                cls._pattern_registry.insert(0, (attributes, adapter_class))
            return adapter_class

        return decorator

    @classmethod
    def register_module(
        cls,
        prefix: str,
        adapter_class: type[InputProtocolAdapter[Any]],
    ) -> None:
        """Register adapter by module prefix (non-decorator form).

        Args:
            prefix: Module path prefix to match
            adapter_class: Adapter class to instantiate when matched
        """
        cls._type_registry[prefix] = adapter_class

    @classmethod
    def register_pattern(
        cls,
        attrs: list[str],
        adapter_class: type[InputProtocolAdapter[Any]],
    ) -> None:
        """Register adapter by attribute pattern (non-decorator form).

        Args:
            attrs: Required attributes for detection
            adapter_class: Adapter class to instantiate when matched
        """
        cls._pattern_registry.insert(0, (attrs, adapter_class))

    @classmethod
    def detect(cls, chunk: Any) -> InputProtocolAdapter[Any] | None:
        """Detect and instantiate appropriate adapter from chunk.

        Detection order:
        1. String → IdentityInputAdapter
        2. Module prefix match
        3. Attribute pattern match
        4. Fallback to text/content attribute
        5. None if no match

        Args:
            chunk: Sample chunk from stream

        Returns:
            Adapter instance if detected, None otherwise
        """
        from hother.streamblocks.adapters.input import (
            AttributeInputAdapter,
            IdentityInputAdapter,
        )

        # Plain text
        if isinstance(chunk, str):
            return IdentityInputAdapter()

        # Module-based detection
        chunk_module = type(chunk).__module__
        for prefix, adapter_class in cls._type_registry.items():
            if chunk_module.startswith(prefix):
                return adapter_class()

        # Attribute-based detection
        for required_attrs, adapter_class in cls._pattern_registry:
            if all(hasattr(chunk, attr) for attr in required_attrs):
                return adapter_class()

        # Fallback: Protocol-based detection
        if isinstance(chunk, HasText):
            return AttributeInputAdapter("text")
        if isinstance(chunk, HasContent):
            return AttributeInputAdapter("content")

        return None

    @classmethod
    def get_registered_modules(cls) -> dict[str, type[InputProtocolAdapter[Any]]]:
        """Get all registered module prefixes.

        Returns:
            Copy of module prefix registry
        """
        return cls._type_registry.copy()

    @classmethod
    def get_registered_patterns(
        cls,
    ) -> list[tuple[list[str], type[InputProtocolAdapter[Any]]]]:
        """Get all registered attribute patterns.

        Returns:
            Copy of attribute pattern registry
        """
        return cls._pattern_registry.copy()

    @classmethod
    def clear(cls) -> None:
        """Clear all registered adapters (useful for testing)."""
        cls._type_registry.clear()
        cls._pattern_registry.clear()


def detect_input_adapter(sample: Any) -> InputProtocolAdapter[Any]:
    """Detect input adapter from sample event.

    Args:
        sample: A sample event from the stream

    Returns:
        Detected adapter instance

    Raises:
        ValueError: If no adapter matches the sample
    """
    adapter = InputAdapterRegistry.detect(sample)
    if adapter is None:
        chunk_type = type(sample)
        registered_modules = list(InputAdapterRegistry.get_registered_modules().keys())
        msg = (
            f"No input adapter found for {chunk_type.__module__}.{chunk_type.__name__}. "
            f"Registered module prefixes: {registered_modules}. "
            f"Consider importing the appropriate extension or registering a custom adapter."
        )
        raise ValueError(msg)
    return adapter
