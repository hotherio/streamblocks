"""Tests for automatic adapter detection."""

from __future__ import annotations

from hother.streamblocks.adapters import (
    AdapterDetector,
    AnthropicAdapter,
    AttributeAdapter,
    GeminiAdapter,
    IdentityAdapter,
    OpenAIAdapter,
)


class TestAdapterDetection:
    """Test automatic adapter detection."""

    def test_detects_plain_text(self):
        """Should use IdentityAdapter for strings."""
        adapter = AdapterDetector.detect("plain text")
        assert isinstance(adapter, IdentityAdapter)

    def test_detects_gemini_by_module(self):
        """Should detect Gemini chunks by module path."""

        # Create a mock class with Gemini-like module
        class GeminiChunk:
            __module__ = "google.genai.types"
            text = "test"

        adapter = AdapterDetector.detect(GeminiChunk())
        assert isinstance(adapter, GeminiAdapter)

    def test_detects_gemini_alt_module(self):
        """Should detect Gemini from alternative module path."""

        class GeminiChunk:
            __module__ = "google.ai.generativelanguage.v1"
            text = "test"

        adapter = AdapterDetector.detect(GeminiChunk())
        assert isinstance(adapter, GeminiAdapter)

    def test_detects_by_attributes(self):
        """Should detect based on attribute patterns."""

        class UnknownChunk:
            text = "content"
            candidates = []  # Gemini-like structure

        adapter = AdapterDetector.detect(UnknownChunk())
        assert isinstance(adapter, GeminiAdapter)

    def test_detects_openai_by_structure(self):
        """Should detect OpenAI chunks by structure."""

        class Delta:
            content = "test"

        class Choice:
            delta = Delta()

        class Chunk:
            choices = [Choice()]
            model = "gpt-4"
            object = "chat.completion.chunk"

        adapter = AdapterDetector.detect(Chunk())
        assert isinstance(adapter, OpenAIAdapter)

    def test_detects_anthropic_by_structure(self):
        """Should detect Anthropic events by structure."""

        class Delta:
            text = "test"

        class Event:
            type = "content_block_delta"
            delta = Delta()

        adapter = AdapterDetector.detect(Event())
        assert isinstance(adapter, AnthropicAdapter)

    def test_fallback_to_attribute_adapter_text(self):
        """Should fall back to AttributeAdapter for unknown types with 'text'."""

        class CustomChunk:
            text = "fallback"

        adapter = AdapterDetector.detect(CustomChunk())
        assert isinstance(adapter, AttributeAdapter)
        assert adapter.text_attr == "text"

    def test_fallback_to_attribute_adapter_content(self):
        """Should fall back to AttributeAdapter for unknown types with 'content'."""

        class CustomChunk:
            content = "fallback"

        adapter = AdapterDetector.detect(CustomChunk())
        assert isinstance(adapter, AttributeAdapter)
        assert adapter.text_attr == "content"

    def test_returns_none_for_unrecognized(self):
        """Should return None for completely unknown formats."""

        class WeirdChunk:
            data = "no standard attributes"

        adapter = AdapterDetector.detect(WeirdChunk())
        assert adapter is None

    def test_custom_adapter_registration_by_module(self):
        """Should use registered custom adapters (module-based)."""

        class MyAdapter:
            def extract_text(self, chunk):
                return chunk.custom_field

        class MyChunk:
            __module__ = "mycompany.ai.types"
            custom_field = "test"

        # Register
        AdapterDetector.register_adapter(
            module_prefix="mycompany.ai",
            adapter_class=MyAdapter,
        )

        try:
            adapter = AdapterDetector.detect(MyChunk())
            assert isinstance(adapter, MyAdapter)
        finally:
            # Cleanup
            AdapterDetector.clear_custom_adapters()

    def test_custom_adapter_registration_by_attributes(self):
        """Should use registered custom adapters (attribute-based)."""

        class MyAdapter:
            def extract_text(self, chunk):
                return chunk.custom_field

        class MyChunk:
            custom_field = "test"
            special_marker = True

        # Register
        AdapterDetector.register_adapter(
            attributes=["custom_field", "special_marker"],
            adapter_class=MyAdapter,
        )

        try:
            adapter = AdapterDetector.detect(MyChunk())
            assert isinstance(adapter, MyAdapter)
        finally:
            # Cleanup
            AdapterDetector.clear_custom_adapters()

    def test_custom_adapters_have_priority(self):
        """Should check custom adapters before built-in ones."""

        class MyAdapter:
            def extract_text(self, chunk):
                return "custom: " + chunk.text

        class Chunk:
            text = "test"

        # Register custom adapter with higher priority
        AdapterDetector.register_adapter(
            attributes=["text"],
            adapter_class=MyAdapter,
        )

        try:
            adapter = AdapterDetector.detect(Chunk())
            # Should use custom adapter, not AttributeAdapter
            assert isinstance(adapter, MyAdapter)
        finally:
            # Cleanup
            AdapterDetector.clear_custom_adapters()

    def test_clear_custom_adapters_resets_to_defaults(self):
        """Should reset to default adapters after clearing."""

        class MyAdapter:
            pass

        # Register custom
        AdapterDetector.register_adapter(
            module_prefix="test.module",
            adapter_class=MyAdapter,
        )

        # Clear
        AdapterDetector.clear_custom_adapters()

        # Should still detect built-in types
        assert isinstance(AdapterDetector.detect("text"), IdentityAdapter)

        class GeminiLike:
            text = "test"
            candidates = []

        assert isinstance(AdapterDetector.detect(GeminiLike()), GeminiAdapter)
