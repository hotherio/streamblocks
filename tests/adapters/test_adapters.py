"""Tests for stream input adapters."""

from __future__ import annotations

from hother.streamblocks.adapters import EventCategory
from hother.streamblocks.adapters.input import (
    AttributeInputAdapter,
    IdentityInputAdapter,
)


class TestIdentityInputAdapter:
    """Test plain text passthrough adapter."""

    def test_extracts_plain_text(self):
        """Should return text unchanged."""
        adapter = IdentityInputAdapter()
        assert adapter.extract_text("Hello world") == "Hello world"
        assert adapter.extract_text("") == ""

    def test_categorizes_as_text_content(self):
        """Should categorize all input as TEXT_CONTENT."""
        adapter = IdentityInputAdapter()
        assert adapter.categorize("any text") == EventCategory.TEXT_CONTENT

    def test_never_signals_completion(self):
        """Plain text streams don't have completion markers."""
        adapter = IdentityInputAdapter()
        assert not adapter.is_complete("any text")

    def test_no_metadata(self):
        """Plain text has no metadata."""
        adapter = IdentityInputAdapter()
        assert adapter.get_metadata("text") is None


class TestAttributeInputAdapter:
    """Test generic attribute extraction adapter."""

    def test_extracts_from_text_attribute(self):
        """Should extract from specified attribute."""

        class Chunk:
            text = "Hello"

        adapter = AttributeInputAdapter("text")
        assert adapter.extract_text(Chunk()) == "Hello"

    def test_extracts_from_custom_attribute(self):
        """Should work with any attribute name."""

        class Chunk:
            content = "World"

        adapter = AttributeInputAdapter("content")
        assert adapter.extract_text(Chunk()) == "World"

    def test_returns_none_when_attribute_missing(self):
        """Should handle missing attributes gracefully."""

        class Chunk:
            pass

        adapter = AttributeInputAdapter("text")
        assert adapter.extract_text(Chunk()) is None

    def test_categorizes_as_text_content(self):
        """Should categorize all input as TEXT_CONTENT."""

        class Chunk:
            text = "test"

        adapter = AttributeInputAdapter("text")
        assert adapter.categorize(Chunk()) == EventCategory.TEXT_CONTENT

    def test_signals_completion_when_finish_reason_present(self):
        """AttributeInputAdapter detects completion via finish_reason."""

        class Chunk:
            text = "Done"
            finish_reason = "stop"

        adapter = AttributeInputAdapter("text")
        assert adapter.is_complete(Chunk())

    def test_no_completion_when_finish_reason_none(self):
        """AttributeInputAdapter returns False when finish_reason is None."""

        class Chunk:
            text = "Not done"
            finish_reason = None

        adapter = AttributeInputAdapter("text")
        assert not adapter.is_complete(Chunk())

    def test_extracts_metadata_when_present(self):
        """AttributeInputAdapter extracts common metadata fields."""

        class Chunk:
            text = "content"
            model = "test-model"
            finish_reason = "stop"

        adapter = AttributeInputAdapter("text")
        metadata = adapter.get_metadata(Chunk())

        assert metadata is not None
        assert metadata["model"] == "test-model"
        assert metadata["finish_reason"] == "stop"

    def test_no_metadata_when_no_common_fields(self):
        """AttributeInputAdapter returns None when no common fields present."""

        class Chunk:
            text = "content"

        adapter = AttributeInputAdapter("text")
        assert adapter.get_metadata(Chunk()) is None


class TestGeminiInputAdapter:
    """Test Google GenAI adapter."""

    def test_extracts_text_from_gemini_chunk(self):
        """Should extract from chunk.text attribute."""
        from hother.streamblocks.extensions.gemini import GeminiInputAdapter

        class GeminiChunk:
            text = "Hello from Gemini"

        adapter = GeminiInputAdapter()
        assert adapter.extract_text(GeminiChunk()) == "Hello from Gemini"

    def test_handles_empty_text(self):
        """Should handle chunks with empty text."""
        from hother.streamblocks.extensions.gemini import GeminiInputAdapter

        class GeminiChunk:
            text = ""

        adapter = GeminiInputAdapter()
        assert adapter.extract_text(GeminiChunk()) == ""

    def test_handles_none_text(self):
        """Should handle chunks with no text attribute."""
        from hother.streamblocks.extensions.gemini import GeminiInputAdapter

        class GeminiChunk:
            pass

        adapter = GeminiInputAdapter()
        assert adapter.extract_text(GeminiChunk()) is None

    def test_categorizes_as_text_content(self):
        """Should categorize all chunks as TEXT_CONTENT."""
        from hother.streamblocks.extensions.gemini import GeminiInputAdapter

        class GeminiChunk:
            text = "test"

        adapter = GeminiInputAdapter()
        assert adapter.categorize(GeminiChunk()) == EventCategory.TEXT_CONTENT

    def test_never_signals_completion(self):
        """Gemini doesn't have explicit completion markers."""
        from hother.streamblocks.extensions.gemini import GeminiInputAdapter

        class GeminiChunk:
            text = "test"

        adapter = GeminiInputAdapter()
        assert not adapter.is_complete(GeminiChunk())

    def test_extracts_usage_metadata(self):
        """Should extract usage information when available."""
        from hother.streamblocks.extensions.gemini import GeminiInputAdapter

        class UsageMetadata:
            prompt_token_count = 10
            candidates_token_count = 20
            total_token_count = 30

        class GeminiChunk:
            text = "response"
            usage_metadata = UsageMetadata()
            model_version = "gemini-2.0"

        adapter = GeminiInputAdapter()
        metadata = adapter.get_metadata(GeminiChunk())

        assert metadata is not None
        assert "usage" in metadata
        assert metadata["usage"].total_token_count == 30
        assert metadata["model"] == "gemini-2.0"


class TestOpenAIInputAdapter:
    """Test OpenAI adapter."""

    def test_extracts_delta_content(self):
        """Should extract from choices[0].delta.content."""
        from hother.streamblocks.extensions.openai import OpenAIInputAdapter

        class Delta:
            content = "Hello"

        class Choice:
            delta = Delta()
            finish_reason = None

        class Chunk:
            choices = [Choice()]

        adapter = OpenAIInputAdapter()
        assert adapter.extract_text(Chunk()) == "Hello"

    def test_handles_none_content(self):
        """Should handle deltas with no content."""
        from hother.streamblocks.extensions.openai import OpenAIInputAdapter

        class Delta:
            role = "assistant"  # First chunk often has role, not content

        class Choice:
            delta = Delta()
            finish_reason = None

        class Chunk:
            choices = [Choice()]

        adapter = OpenAIInputAdapter()
        assert adapter.extract_text(Chunk()) is None

    def test_handles_empty_choices(self):
        """Should handle chunks with empty choices array."""
        from hother.streamblocks.extensions.openai import OpenAIInputAdapter

        class Chunk:
            choices = []

        adapter = OpenAIInputAdapter()
        assert adapter.extract_text(Chunk()) is None

    def test_categorizes_as_text_content(self):
        """Should categorize all chunks as TEXT_CONTENT."""
        from hother.streamblocks.extensions.openai import OpenAIInputAdapter

        class Delta:
            content = "test"

        class Choice:
            delta = Delta()
            finish_reason = None

        class Chunk:
            choices = [Choice()]

        adapter = OpenAIInputAdapter()
        assert adapter.categorize(Chunk()) == EventCategory.TEXT_CONTENT

    def test_detects_completion(self):
        """Should detect when finish_reason is set."""
        from hother.streamblocks.extensions.openai import OpenAIInputAdapter

        class Delta:
            pass

        class Choice:
            delta = Delta()
            finish_reason = "stop"

        class Chunk:
            choices = [Choice()]

        adapter = OpenAIInputAdapter()
        assert adapter.is_complete(Chunk())

    def test_no_completion_when_finish_reason_none(self):
        """Should not signal completion when finish_reason is None."""
        from hother.streamblocks.extensions.openai import OpenAIInputAdapter

        class Delta:
            content = "test"

        class Choice:
            delta = Delta()
            finish_reason = None

        class Chunk:
            choices = [Choice()]

        adapter = OpenAIInputAdapter()
        assert not adapter.is_complete(Chunk())

    def test_extracts_finish_metadata(self):
        """Should extract model and finish reason."""
        from hother.streamblocks.extensions.openai import OpenAIInputAdapter

        class Delta:
            pass

        class Choice:
            delta = Delta()
            finish_reason = "length"

        class Chunk:
            model = "gpt-4"
            choices = [Choice()]

        adapter = OpenAIInputAdapter()
        metadata = adapter.get_metadata(Chunk())

        assert metadata is not None
        assert metadata["model"] == "gpt-4"
        assert metadata["finish_reason"] == "length"


class TestAnthropicInputAdapter:
    """Test Anthropic adapter."""

    def test_extracts_text_from_content_delta(self):
        """Should extract from content_block_delta events."""
        from hother.streamblocks.extensions.anthropic import AnthropicInputAdapter

        class TextDelta:
            text = "Hello"

        class Event:
            type = "content_block_delta"
            delta = TextDelta()

        adapter = AnthropicInputAdapter()
        assert adapter.extract_text(Event()) == "Hello"

    def test_ignores_non_text_events(self):
        """Should return None for events without text."""
        from hother.streamblocks.extensions.anthropic import AnthropicInputAdapter

        class Event:
            type = "message_start"

        adapter = AnthropicInputAdapter()
        assert adapter.extract_text(Event()) is None

    def test_handles_missing_delta(self):
        """Should handle events with no delta attribute."""
        from hother.streamblocks.extensions.anthropic import AnthropicInputAdapter

        class Event:
            type = "content_block_delta"

        adapter = AnthropicInputAdapter()
        assert adapter.extract_text(Event()) is None

    def test_categorizes_text_events_as_text_content(self):
        """Should categorize text events as TEXT_CONTENT."""
        from hother.streamblocks.extensions.anthropic import AnthropicInputAdapter

        class TextDelta:
            text = "test"

        class Event:
            type = "content_block_delta"
            delta = TextDelta()

        adapter = AnthropicInputAdapter()
        assert adapter.categorize(Event()) == EventCategory.TEXT_CONTENT

    def test_categorizes_non_text_events_as_passthrough(self):
        """Should categorize non-text events as PASSTHROUGH."""
        from hother.streamblocks.extensions.anthropic import AnthropicInputAdapter

        class Event:
            type = "message_start"

        adapter = AnthropicInputAdapter()
        assert adapter.categorize(Event()) == EventCategory.PASSTHROUGH

    def test_detects_message_stop(self):
        """Should detect stream completion."""
        from hother.streamblocks.extensions.anthropic import AnthropicInputAdapter

        class Event:
            type = "message_stop"

        adapter = AnthropicInputAdapter()
        assert adapter.is_complete(Event())

    def test_no_completion_for_other_events(self):
        """Should not signal completion for other event types."""
        from hother.streamblocks.extensions.anthropic import AnthropicInputAdapter

        class Event:
            type = "content_block_delta"

        adapter = AnthropicInputAdapter()
        assert not adapter.is_complete(Event())

    def test_extracts_stop_reason(self):
        """Should extract stop reason from message_stop event."""
        from hother.streamblocks.extensions.anthropic import AnthropicInputAdapter

        class Event:
            type = "message_stop"
            stop_reason = "end_turn"

        adapter = AnthropicInputAdapter()
        metadata = adapter.get_metadata(Event())

        assert metadata is not None
        assert metadata["stop_reason"] == "end_turn"

    def test_extracts_usage_from_message_delta(self):
        """Should extract usage from delta events."""
        from hother.streamblocks.extensions.anthropic import AnthropicInputAdapter

        class Usage:
            input_tokens = 10
            output_tokens = 20

        class Event:
            type = "message_delta"
            usage = Usage()

        adapter = AnthropicInputAdapter()
        metadata = adapter.get_metadata(Event())

        assert metadata is not None
        assert "usage" in metadata
        assert metadata["usage"].output_tokens == 20
