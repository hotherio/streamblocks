"""Tests for stream adapters."""

from __future__ import annotations

from hother.streamblocks.adapters import (
    AnthropicAdapter,
    AttributeAdapter,
    CallableAdapter,
    GeminiAdapter,
    IdentityAdapter,
    OpenAIAdapter,
)


class TestIdentityAdapter:
    """Test plain text passthrough adapter."""

    def test_extracts_plain_text(self):
        """Should return text unchanged."""
        adapter = IdentityAdapter()
        assert adapter.extract_text("Hello world") == "Hello world"
        assert adapter.extract_text("") == ""

    def test_never_signals_completion(self):
        """Plain text streams don't have completion markers."""
        adapter = IdentityAdapter()
        assert not adapter.is_complete("any text")

    def test_no_metadata(self):
        """Plain text has no metadata."""
        adapter = IdentityAdapter()
        assert adapter.get_metadata("text") is None


class TestAttributeAdapter:
    """Test generic attribute extraction adapter."""

    def test_extracts_from_text_attribute(self):
        """Should extract from specified attribute."""

        class Chunk:
            text = "Hello"

        adapter = AttributeAdapter("text")
        assert adapter.extract_text(Chunk()) == "Hello"

    def test_extracts_from_custom_attribute(self):
        """Should work with any attribute name."""

        class Chunk:
            content = "World"

        adapter = AttributeAdapter("content")
        assert adapter.extract_text(Chunk()) == "World"

    def test_returns_none_when_attribute_missing(self):
        """Should handle missing attributes gracefully."""

        class Chunk:
            pass

        adapter = AttributeAdapter("text")
        assert adapter.extract_text(Chunk()) is None

    def test_detects_completion_from_finish_reason(self):
        """Should check finish_reason for completion."""

        class Chunk:
            text = "Done"
            finish_reason = "stop"

        adapter = AttributeAdapter("text")
        assert adapter.is_complete(Chunk())

    def test_no_completion_when_finish_reason_none(self):
        """Should not signal completion when finish_reason is None."""

        class Chunk:
            text = "Not done"
            finish_reason = None

        adapter = AttributeAdapter("text")
        assert not adapter.is_complete(Chunk())

    def test_extracts_metadata(self):
        """Should extract common metadata fields."""

        class Chunk:
            text = "content"
            finish_reason = "stop"
            model = "test-model"

        adapter = AttributeAdapter("text")
        metadata = adapter.get_metadata(Chunk())

        assert metadata is not None
        assert metadata["finish_reason"] == "stop"
        assert metadata["model"] == "test-model"


class TestGeminiAdapter:
    """Test Google GenAI adapter."""

    def test_extracts_text_from_gemini_chunk(self):
        """Should extract from chunk.text attribute."""

        class GeminiChunk:
            text = "Hello from Gemini"

        adapter = GeminiAdapter()
        assert adapter.extract_text(GeminiChunk()) == "Hello from Gemini"

    def test_handles_empty_text(self):
        """Should handle chunks with empty text."""

        class GeminiChunk:
            text = ""

        adapter = GeminiAdapter()
        assert adapter.extract_text(GeminiChunk()) == ""

    def test_handles_none_text(self):
        """Should handle chunks with no text attribute."""

        class GeminiChunk:
            pass

        adapter = GeminiAdapter()
        assert adapter.extract_text(GeminiChunk()) is None

    def test_never_signals_completion(self):
        """Gemini doesn't have explicit completion markers."""

        class GeminiChunk:
            text = "test"

        adapter = GeminiAdapter()
        assert not adapter.is_complete(GeminiChunk())

    def test_extracts_usage_metadata(self):
        """Should extract usage information when available."""

        class UsageMetadata:
            prompt_token_count = 10
            candidates_token_count = 20
            total_token_count = 30

        class GeminiChunk:
            text = "response"
            usage_metadata = UsageMetadata()
            model_version = "gemini-2.0"

        adapter = GeminiAdapter()
        metadata = adapter.get_metadata(GeminiChunk())

        assert metadata is not None
        assert "usage" in metadata
        assert metadata["usage"].total_token_count == 30
        assert metadata["model"] == "gemini-2.0"


class TestOpenAIAdapter:
    """Test OpenAI adapter."""

    def test_extracts_delta_content(self):
        """Should extract from choices[0].delta.content."""

        class Delta:
            content = "Hello"

        class Choice:
            delta = Delta()
            finish_reason = None

        class Chunk:
            choices = [Choice()]

        adapter = OpenAIAdapter()
        assert adapter.extract_text(Chunk()) == "Hello"

    def test_handles_none_content(self):
        """Should handle deltas with no content."""

        class Delta:
            role = "assistant"  # First chunk often has role, not content

        class Choice:
            delta = Delta()
            finish_reason = None

        class Chunk:
            choices = [Choice()]

        adapter = OpenAIAdapter()
        assert adapter.extract_text(Chunk()) is None

    def test_handles_empty_choices(self):
        """Should handle chunks with empty choices array."""

        class Chunk:
            choices = []

        adapter = OpenAIAdapter()
        assert adapter.extract_text(Chunk()) is None

    def test_detects_completion(self):
        """Should detect when finish_reason is set."""

        class Delta:
            pass

        class Choice:
            delta = Delta()
            finish_reason = "stop"

        class Chunk:
            choices = [Choice()]

        adapter = OpenAIAdapter()
        assert adapter.is_complete(Chunk())

    def test_no_completion_when_finish_reason_none(self):
        """Should not signal completion when finish_reason is None."""

        class Delta:
            content = "test"

        class Choice:
            delta = Delta()
            finish_reason = None

        class Chunk:
            choices = [Choice()]

        adapter = OpenAIAdapter()
        assert not adapter.is_complete(Chunk())

    def test_extracts_finish_metadata(self):
        """Should extract model and finish reason."""

        class Delta:
            pass

        class Choice:
            delta = Delta()
            finish_reason = "length"

        class Chunk:
            model = "gpt-4"
            choices = [Choice()]

        adapter = OpenAIAdapter()
        metadata = adapter.get_metadata(Chunk())

        assert metadata is not None
        assert metadata["model"] == "gpt-4"
        assert metadata["finish_reason"] == "length"


class TestAnthropicAdapter:
    """Test Anthropic adapter."""

    def test_extracts_text_from_content_delta(self):
        """Should extract from content_block_delta events."""

        class TextDelta:
            text = "Hello"

        class Event:
            type = "content_block_delta"
            delta = TextDelta()

        adapter = AnthropicAdapter()
        assert adapter.extract_text(Event()) == "Hello"

    def test_ignores_non_text_events(self):
        """Should return None for events without text."""

        class Event:
            type = "message_start"

        adapter = AnthropicAdapter()
        assert adapter.extract_text(Event()) is None

    def test_handles_missing_delta(self):
        """Should handle events with no delta attribute."""

        class Event:
            type = "content_block_delta"

        adapter = AnthropicAdapter()
        assert adapter.extract_text(Event()) is None

    def test_detects_message_stop(self):
        """Should detect stream completion."""

        class Event:
            type = "message_stop"

        adapter = AnthropicAdapter()
        assert adapter.is_complete(Event())

    def test_no_completion_for_other_events(self):
        """Should not signal completion for other event types."""

        class Event:
            type = "content_block_delta"

        adapter = AnthropicAdapter()
        assert not adapter.is_complete(Event())

    def test_extracts_stop_reason(self):
        """Should extract stop reason from message_stop."""

        class Event:
            type = "message_stop"
            stop_reason = "end_turn"

        adapter = AnthropicAdapter()
        metadata = adapter.get_metadata(Event())

        assert metadata is not None
        assert metadata["stop_reason"] == "end_turn"

    def test_extracts_usage_from_message_delta(self):
        """Should extract usage from delta events."""

        class Usage:
            input_tokens = 10
            output_tokens = 20

        class Event:
            type = "message_delta"
            usage = Usage()

        adapter = AnthropicAdapter()
        metadata = adapter.get_metadata(Event())

        assert metadata is not None
        assert "usage" in metadata
        assert metadata["usage"].output_tokens == 20


class TestCallableAdapter:
    """Test custom function-based adapter."""

    def test_uses_custom_extraction_function(self):
        """Should call user-provided extraction function."""

        def extract(chunk):
            return chunk.get("text")

        adapter = CallableAdapter(extract_fn=extract)
        assert adapter.extract_text({"text": "custom"}) == "custom"

    def test_uses_custom_completion_function(self):
        """Should call user-provided completion check."""

        def is_done(chunk):
            return chunk.get("done", False)

        adapter = CallableAdapter(
            extract_fn=lambda c: c.get("text"),
            is_complete_fn=is_done,
        )

        assert adapter.is_complete({"done": True})
        assert not adapter.is_complete({"done": False})

    def test_uses_custom_metadata_function(self):
        """Should call user-provided metadata extractor."""

        def get_meta(chunk):
            if "usage" in chunk:
                return {"tokens": chunk["usage"]["total"]}
            return None

        adapter = CallableAdapter(
            extract_fn=lambda c: c.get("text"),
            metadata_fn=get_meta,
        )

        metadata = adapter.get_metadata({"usage": {"total": 100}})
        assert metadata is not None
        assert metadata["tokens"] == 100

    def test_default_completion_function(self):
        """Should default to never completing."""
        adapter = CallableAdapter(extract_fn=lambda c: c.get("text"))
        assert not adapter.is_complete({"text": "test"})

    def test_no_metadata_when_function_not_provided(self):
        """Should return None when metadata function not provided."""
        adapter = CallableAdapter(extract_fn=lambda c: c.get("text"))
        assert adapter.get_metadata({"text": "test"}) is None
