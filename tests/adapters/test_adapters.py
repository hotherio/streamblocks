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

    def test_no_completion_when_no_finish_reason_attribute(self):
        """AttributeInputAdapter returns False when event has no finish_reason attribute.

        This covers line 163 of identity.py (the fallback return False).
        """

        class Chunk:
            text = "content"
            # No finish_reason attribute at all

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
        from google.genai.types import GenerateContentResponse

        from hother.streamblocks.extensions.gemini import GeminiInputAdapter

        # Create a real GenerateContentResponse with text
        response = GenerateContentResponse(candidates=[{"content": {"parts": [{"text": "Hello from Gemini"}]}}])

        adapter = GeminiInputAdapter()
        assert adapter.extract_text(response) == "Hello from Gemini"

    def test_handles_empty_text(self):
        """Should handle chunks with empty text."""
        from google.genai.types import GenerateContentResponse

        from hother.streamblocks.extensions.gemini import GeminiInputAdapter

        # Create response with empty text
        response = GenerateContentResponse(candidates=[{"content": {"parts": [{"text": ""}]}}])

        adapter = GeminiInputAdapter()
        assert adapter.extract_text(response) == ""

    def test_handles_none_text(self):
        """Should handle chunks with no text (no candidates)."""
        from google.genai.types import GenerateContentResponse

        from hother.streamblocks.extensions.gemini import GeminiInputAdapter

        # Create response with no candidates
        response = GenerateContentResponse(candidates=[])

        adapter = GeminiInputAdapter()
        # When there are no candidates, text property returns None
        assert adapter.extract_text(response) is None

    def test_categorizes_as_text_content(self):
        """Should categorize all chunks as TEXT_CONTENT."""
        from google.genai.types import GenerateContentResponse

        from hother.streamblocks.extensions.gemini import GeminiInputAdapter

        response = GenerateContentResponse(candidates=[{"content": {"parts": [{"text": "test"}]}}])

        adapter = GeminiInputAdapter()
        assert adapter.categorize(response) == EventCategory.TEXT_CONTENT

    def test_never_signals_completion(self):
        """Gemini doesn't have explicit completion markers."""
        from google.genai.types import GenerateContentResponse

        from hother.streamblocks.extensions.gemini import GeminiInputAdapter

        response = GenerateContentResponse(candidates=[{"content": {"parts": [{"text": "test"}]}}])

        adapter = GeminiInputAdapter()
        assert not adapter.is_complete(response)

    def test_extracts_usage_metadata(self):
        """Should extract usage information when available."""
        from google.genai.types import GenerateContentResponse

        from hother.streamblocks.extensions.gemini import GeminiInputAdapter

        # Create response with usage metadata
        response = GenerateContentResponse(
            candidates=[{"content": {"parts": [{"text": "response"}]}}],
            usage_metadata={"prompt_token_count": 10, "candidates_token_count": 20, "total_token_count": 30},
            model_version="gemini-2.0",
        )

        adapter = GeminiInputAdapter()
        metadata = adapter.get_metadata(response)

        assert metadata is not None
        assert "usage" in metadata
        assert metadata["usage"].total_token_count == 30
        assert metadata["model"] == "gemini-2.0"


class TestOpenAIInputAdapter:
    """Test OpenAI adapter."""

    def test_extracts_delta_content(self):
        """Should extract from choices[0].delta.content."""
        from openai.types.chat import ChatCompletionChunk
        from openai.types.chat.chat_completion_chunk import Choice, ChoiceDelta

        from hother.streamblocks.extensions.openai import OpenAIInputAdapter

        chunk = ChatCompletionChunk(
            id="test",
            created=0,
            model="gpt-4",
            object="chat.completion.chunk",
            choices=[Choice(index=0, delta=ChoiceDelta(content="Hello"), finish_reason=None)],
        )

        adapter = OpenAIInputAdapter()
        assert adapter.extract_text(chunk) == "Hello"

    def test_handles_none_content(self):
        """Should handle deltas with no content."""
        from openai.types.chat import ChatCompletionChunk
        from openai.types.chat.chat_completion_chunk import Choice, ChoiceDelta

        from hother.streamblocks.extensions.openai import OpenAIInputAdapter

        # Delta with role but no content (first chunk pattern)
        chunk = ChatCompletionChunk(
            id="test",
            created=0,
            model="gpt-4",
            object="chat.completion.chunk",
            choices=[Choice(index=0, delta=ChoiceDelta(role="assistant"), finish_reason=None)],
        )

        adapter = OpenAIInputAdapter()
        assert adapter.extract_text(chunk) is None

    def test_handles_empty_choices(self):
        """Should handle chunks with empty choices array."""
        from openai.types.chat import ChatCompletionChunk

        from hother.streamblocks.extensions.openai import OpenAIInputAdapter

        chunk = ChatCompletionChunk(
            id="test",
            created=0,
            model="gpt-4",
            object="chat.completion.chunk",
            choices=[],
        )

        adapter = OpenAIInputAdapter()
        assert adapter.extract_text(chunk) is None

    def test_categorizes_as_text_content(self):
        """Should categorize all chunks as TEXT_CONTENT."""
        from openai.types.chat import ChatCompletionChunk
        from openai.types.chat.chat_completion_chunk import Choice, ChoiceDelta

        from hother.streamblocks.extensions.openai import OpenAIInputAdapter

        chunk = ChatCompletionChunk(
            id="test",
            created=0,
            model="gpt-4",
            object="chat.completion.chunk",
            choices=[Choice(index=0, delta=ChoiceDelta(content="test"), finish_reason=None)],
        )

        adapter = OpenAIInputAdapter()
        assert adapter.categorize(chunk) == EventCategory.TEXT_CONTENT

    def test_detects_completion(self):
        """Should detect when finish_reason is set."""
        from openai.types.chat import ChatCompletionChunk
        from openai.types.chat.chat_completion_chunk import Choice, ChoiceDelta

        from hother.streamblocks.extensions.openai import OpenAIInputAdapter

        chunk = ChatCompletionChunk(
            id="test",
            created=0,
            model="gpt-4",
            object="chat.completion.chunk",
            choices=[Choice(index=0, delta=ChoiceDelta(), finish_reason="stop")],
        )

        adapter = OpenAIInputAdapter()
        assert adapter.is_complete(chunk)

    def test_no_completion_when_finish_reason_none(self):
        """Should not signal completion when finish_reason is None."""
        from openai.types.chat import ChatCompletionChunk
        from openai.types.chat.chat_completion_chunk import Choice, ChoiceDelta

        from hother.streamblocks.extensions.openai import OpenAIInputAdapter

        chunk = ChatCompletionChunk(
            id="test",
            created=0,
            model="gpt-4",
            object="chat.completion.chunk",
            choices=[Choice(index=0, delta=ChoiceDelta(content="test"), finish_reason=None)],
        )

        adapter = OpenAIInputAdapter()
        assert not adapter.is_complete(chunk)

    def test_extracts_finish_metadata(self):
        """Should extract model and finish reason."""
        from openai.types.chat import ChatCompletionChunk
        from openai.types.chat.chat_completion_chunk import Choice, ChoiceDelta

        from hother.streamblocks.extensions.openai import OpenAIInputAdapter

        chunk = ChatCompletionChunk(
            id="test",
            created=0,
            model="gpt-4",
            object="chat.completion.chunk",
            choices=[Choice(index=0, delta=ChoiceDelta(), finish_reason="length")],
        )

        adapter = OpenAIInputAdapter()
        metadata = adapter.get_metadata(chunk)

        assert metadata is not None
        assert metadata["model"] == "gpt-4"
        assert metadata["finish_reason"] == "length"


class TestAnthropicInputAdapter:
    """Test Anthropic adapter."""

    def test_extracts_text_from_content_delta(self):
        """Should extract from content_block_delta events."""
        from anthropic.types import ContentBlockDeltaEvent, TextDelta

        from hother.streamblocks.extensions.anthropic import AnthropicInputAdapter

        # Create a real ContentBlockDeltaEvent with TextDelta
        text_delta = TextDelta(text="Hello", type="text_delta")
        event = ContentBlockDeltaEvent(delta=text_delta, index=0, type="content_block_delta")

        adapter = AnthropicInputAdapter()
        assert adapter.extract_text(event) == "Hello"

    def test_returns_none_for_non_text_events(self):
        """Should return None for events that don't contain text."""
        from anthropic.types import MessageStopEvent

        from hother.streamblocks.extensions.anthropic import AnthropicInputAdapter

        # MessageStopEvent has no text
        event = MessageStopEvent(type="message_stop")

        adapter = AnthropicInputAdapter()
        assert adapter.extract_text(event) is None

    def test_returns_none_for_non_text_delta(self):
        """Should return None for content_block_delta with non-text delta."""
        from anthropic.types import ContentBlockDeltaEvent
        from anthropic.types.input_json_delta import InputJSONDelta

        from hother.streamblocks.extensions.anthropic import AnthropicInputAdapter

        # ContentBlockDeltaEvent with InputJSONDelta (not TextDelta)
        json_delta = InputJSONDelta(partial_json='{"key":', type="input_json_delta")
        event = ContentBlockDeltaEvent(delta=json_delta, index=0, type="content_block_delta")

        adapter = AnthropicInputAdapter()
        assert adapter.extract_text(event) is None

    def test_categorizes_text_events_as_text_content(self):
        """Should categorize content_block_delta events as TEXT_CONTENT."""
        from anthropic.types import ContentBlockDeltaEvent, TextDelta

        from hother.streamblocks.extensions.anthropic import AnthropicInputAdapter

        text_delta = TextDelta(text="test", type="text_delta")
        event = ContentBlockDeltaEvent(delta=text_delta, index=0, type="content_block_delta")

        adapter = AnthropicInputAdapter()
        assert adapter.categorize(event) == EventCategory.TEXT_CONTENT

    def test_categorizes_non_text_events_as_passthrough(self):
        """Should categorize non-content_block_delta events as PASSTHROUGH."""
        from anthropic.types import MessageStopEvent

        from hother.streamblocks.extensions.anthropic import AnthropicInputAdapter

        event = MessageStopEvent(type="message_stop")

        adapter = AnthropicInputAdapter()
        assert adapter.categorize(event) == EventCategory.PASSTHROUGH

    def test_detects_message_stop(self):
        """Should detect stream completion via MessageStopEvent."""
        from anthropic.types import MessageStopEvent

        from hother.streamblocks.extensions.anthropic import AnthropicInputAdapter

        event = MessageStopEvent(type="message_stop")

        adapter = AnthropicInputAdapter()
        assert adapter.is_complete(event)

    def test_no_completion_for_other_events(self):
        """Should not signal completion for non-MessageStopEvent events."""
        from anthropic.types import ContentBlockDeltaEvent, TextDelta

        from hother.streamblocks.extensions.anthropic import AnthropicInputAdapter

        text_delta = TextDelta(text="test", type="text_delta")
        event = ContentBlockDeltaEvent(delta=text_delta, index=0, type="content_block_delta")

        adapter = AnthropicInputAdapter()
        assert not adapter.is_complete(event)

    def test_message_stop_has_no_metadata(self):
        """MessageStopEvent returns no metadata (stop_reason is in MessageDeltaEvent)."""
        from anthropic.types import MessageStopEvent

        from hother.streamblocks.extensions.anthropic import AnthropicInputAdapter

        event = MessageStopEvent(type="message_stop")

        adapter = AnthropicInputAdapter()
        metadata = adapter.get_metadata(event)

        assert metadata is None

    def test_extracts_usage_from_message_delta(self):
        """Should extract usage from MessageDeltaEvent."""
        from anthropic.types import MessageDeltaEvent
        from anthropic.types.message_delta_usage import MessageDeltaUsage
        from anthropic.types.raw_message_delta_event import Delta

        from hother.streamblocks.extensions.anthropic import AnthropicInputAdapter

        delta = Delta(stop_reason="end_turn", stop_sequence=None)
        usage = MessageDeltaUsage(output_tokens=20)
        event = MessageDeltaEvent(delta=delta, type="message_delta", usage=usage)

        adapter = AnthropicInputAdapter()
        metadata = adapter.get_metadata(event)

        assert metadata is not None
        assert "usage" in metadata
        assert metadata["usage"].output_tokens == 20


class TestStreamBlocksOutputAdapter:
    """Tests for StreamBlocksOutputAdapter."""

    def test_to_protocol_event_passes_through(self):
        """Should return event unchanged."""
        from hother.streamblocks.adapters.output.streamblocks import StreamBlocksOutputAdapter
        from hother.streamblocks.core.types import TextContentEvent

        adapter = StreamBlocksOutputAdapter()
        event = TextContentEvent(content="test", line_number=1)

        result = adapter.to_protocol_event(event)

        assert result is event

    def test_passthrough_returns_none(self):
        """passthrough should return None (not applicable for native output).

        This covers line 50 of output/streamblocks.py.
        """
        from hother.streamblocks.adapters.output.streamblocks import StreamBlocksOutputAdapter

        adapter = StreamBlocksOutputAdapter()

        result = adapter.passthrough({"any": "event"})

        assert result is None


class TestProtocolDefaultMethods:
    """Tests for protocol default method implementations."""

    def test_identity_adapter_get_metadata_returns_none(self):
        """IdentityInputAdapter.get_metadata should return None.

        This covers line 75 of protocols.py via IdentityInputAdapter implementation.
        """
        adapter = IdentityInputAdapter()
        result = adapter.get_metadata("any text")
        assert result is None

    def test_identity_adapter_is_complete_returns_false(self):
        """IdentityInputAdapter.is_complete should return False.

        This covers line 86 of protocols.py via IdentityInputAdapter implementation.
        """
        adapter = IdentityInputAdapter()
        result = adapter.is_complete("any text")
        assert result is False

    def test_protocol_default_get_metadata(self):
        """Test that protocol default get_metadata returns None.

        This directly covers line 75 of protocols.py by using
        the protocol's default implementation.
        """
        from hother.streamblocks.adapters.protocols import InputProtocolAdapter

        # Create a minimal adapter class that only implements required methods
        # and relies on defaults for optional methods
        class MinimalAdapter:
            def categorize(self, event):
                return EventCategory.TEXT_CONTENT

            def extract_text(self, event):
                return str(event)

        adapter = MinimalAdapter()

        # Call get_metadata via the protocol's default implementation
        # Since MinimalAdapter doesn't override get_metadata,
        # we access the protocol default directly
        result = InputProtocolAdapter.get_metadata(adapter, "test")
        assert result is None

    def test_protocol_default_is_complete(self):
        """Test that protocol default is_complete returns False.

        This directly covers line 86 of protocols.py by using
        the protocol's default implementation.
        """
        from hother.streamblocks.adapters.protocols import InputProtocolAdapter

        class MinimalAdapter:
            def categorize(self, event):
                return EventCategory.TEXT_CONTENT

            def extract_text(self, event):
                return str(event)

        adapter = MinimalAdapter()

        # Call is_complete via the protocol's default implementation
        result = InputProtocolAdapter.is_complete(adapter, "test")
        assert result is False
