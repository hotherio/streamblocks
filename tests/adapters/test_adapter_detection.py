"""Tests for automatic adapter detection via InputAdapterRegistry."""

from __future__ import annotations

import hother.streamblocks.extensions.anthropic

# Import extensions to register their adapters
import hother.streamblocks.extensions.gemini
import hother.streamblocks.extensions.openai  # noqa: F401
from hother.streamblocks.adapters import (
    EventCategory,
    InputAdapterRegistry,
    detect_input_adapter,
)
from hother.streamblocks.adapters.input import (
    AttributeInputAdapter,
    IdentityInputAdapter,
)


class TestInputAdapterRegistry:
    """Test automatic adapter detection via InputAdapterRegistry."""

    def test_detects_plain_text(self):
        """Should use IdentityInputAdapter for strings."""
        adapter = InputAdapterRegistry.detect("plain text")
        assert isinstance(adapter, IdentityInputAdapter)

    def test_identity_adapter_categorizes_as_text_content(self):
        """IdentityInputAdapter should categorize all input as TEXT_CONTENT."""
        adapter = IdentityInputAdapter()
        assert adapter.categorize("any text") == EventCategory.TEXT_CONTENT

    def test_identity_adapter_extracts_text(self):
        """IdentityInputAdapter should return text unchanged."""
        adapter = IdentityInputAdapter()
        assert adapter.extract_text("Hello world") == "Hello world"

    def test_detects_gemini_by_module(self):
        """Should detect Gemini chunks by module path."""
        from hother.streamblocks.extensions.gemini import GeminiInputAdapter

        # Create a mock class with Gemini-like module
        class GeminiChunk:
            __module__ = "google.genai.types"
            text = "test"

        adapter = InputAdapterRegistry.detect(GeminiChunk())
        assert isinstance(adapter, GeminiInputAdapter)

    def test_detects_openai_by_module(self):
        """Should detect OpenAI chunks by module path."""
        from hother.streamblocks.extensions.openai import OpenAIInputAdapter

        class Delta:
            content = "test"

        class Choice:
            delta = Delta()
            finish_reason = None

        class OpenAIChunk:
            __module__ = "openai.types.chat"
            choices = [Choice()]

        adapter = InputAdapterRegistry.detect(OpenAIChunk())
        assert isinstance(adapter, OpenAIInputAdapter)

    def test_detects_anthropic_by_module(self):
        """Should detect Anthropic events by module path."""
        from hother.streamblocks.extensions.anthropic import AnthropicInputAdapter

        class AnthropicEvent:
            __module__ = "anthropic.types"
            type = "content_block_delta"

        adapter = InputAdapterRegistry.detect(AnthropicEvent())
        assert isinstance(adapter, AnthropicInputAdapter)

    def test_fallback_to_attribute_adapter_text(self):
        """Should fall back to AttributeInputAdapter for unknown types with 'text'."""

        class CustomChunk:
            text = "fallback"

        adapter = InputAdapterRegistry.detect(CustomChunk())
        assert isinstance(adapter, AttributeInputAdapter)
        assert adapter.text_attr == "text"

    def test_fallback_to_attribute_adapter_content(self):
        """Should fall back to AttributeInputAdapter for unknown types with 'content'."""

        class CustomChunk:
            content = "fallback"

        adapter = InputAdapterRegistry.detect(CustomChunk())
        assert isinstance(adapter, AttributeInputAdapter)
        assert adapter.text_attr == "content"

    def test_returns_none_for_unrecognized(self):
        """Should return None for completely unknown formats."""

        class WeirdChunk:
            data = "no standard attributes"

        adapter = InputAdapterRegistry.detect(WeirdChunk())
        assert adapter is None

    def test_detect_input_adapter_raises_for_unknown(self):
        """detect_input_adapter should raise ValueError for unknown formats."""
        import pytest

        class WeirdChunk:
            data = "no standard attributes"

        with pytest.raises(ValueError, match="No input adapter found"):
            detect_input_adapter(WeirdChunk())

    def test_custom_adapter_registration_by_module(self):
        """Should use registered custom adapters (module-based)."""

        class MyInputAdapter:
            def categorize(self, event):
                return EventCategory.TEXT_CONTENT

            def extract_text(self, chunk):
                return chunk.custom_field

            def get_metadata(self, chunk):
                return None

            def is_complete(self, chunk):
                return False

        class MyChunk:
            __module__ = "mycompany.ai.types"
            custom_field = "test"

        # Register
        InputAdapterRegistry.register_module("mycompany.ai", MyInputAdapter)

        try:
            adapter = InputAdapterRegistry.detect(MyChunk())
            assert isinstance(adapter, MyInputAdapter)
        finally:
            # Cleanup - remove from registry
            del InputAdapterRegistry._type_registry["mycompany.ai"]

    def test_custom_adapter_registration_by_attributes(self):
        """Should use registered custom adapters (attribute-based)."""

        class MyInputAdapter:
            def categorize(self, event):
                return EventCategory.TEXT_CONTENT

            def extract_text(self, chunk):
                return chunk.custom_field

            def get_metadata(self, chunk):
                return None

            def is_complete(self, chunk):
                return False

        class MyChunk:
            custom_field = "test"
            special_marker = True

        # Register
        InputAdapterRegistry.register_pattern(
            ["custom_field", "special_marker"],
            MyInputAdapter,
        )

        try:
            adapter = InputAdapterRegistry.detect(MyChunk())
            assert isinstance(adapter, MyInputAdapter)
        finally:
            # Cleanup - remove from pattern registry
            InputAdapterRegistry._pattern_registry = [
                (attrs, cls) for attrs, cls in InputAdapterRegistry._pattern_registry if cls is not MyInputAdapter
            ]

    def test_get_registered_modules(self):
        """Should return copy of registered modules."""
        modules = InputAdapterRegistry.get_registered_modules()
        assert isinstance(modules, dict)
        # Extensions should be registered
        assert any("google" in key or "gemini" in key.lower() for key in modules)

    def test_get_registered_patterns(self):
        """Should return copy of registered patterns."""
        patterns = InputAdapterRegistry.get_registered_patterns()
        assert isinstance(patterns, list)

    def test_register_decorator(self):
        """Should work as a decorator."""

        @InputAdapterRegistry.register(module_prefix="test.decorator.module")
        class DecoratorTestAdapter:
            def categorize(self, event):
                return EventCategory.TEXT_CONTENT

            def extract_text(self, chunk):
                return "decorated"

            def get_metadata(self, chunk):
                return None

            def is_complete(self, chunk):
                return False

        class TestChunk:
            __module__ = "test.decorator.module.types"

        try:
            adapter = InputAdapterRegistry.detect(TestChunk())
            assert isinstance(adapter, DecoratorTestAdapter)
        finally:
            # Cleanup
            del InputAdapterRegistry._type_registry["test.decorator.module"]
