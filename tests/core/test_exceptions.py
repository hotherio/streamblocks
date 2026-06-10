"""Tests for the Streamblocks exception hierarchy."""

import pytest

from hother.streamblocks import (
    AdapterDetectionError,
    AdapterNotConfiguredError,
    StreamblocksError,
    SyntaxConfigError,
)


class TestStreamblocksError:
    """Tests for the base exception class."""

    def test_is_exception_subclass(self) -> None:
        """The base class is a plain Exception subclass."""
        assert issubclass(StreamblocksError, Exception)

    @pytest.mark.parametrize(
        "subclass",
        [AdapterNotConfiguredError, AdapterDetectionError, SyntaxConfigError],
    )
    def test_subclasses_share_base(self, subclass: type[StreamblocksError]) -> None:
        """Every concrete exception derives from StreamblocksError."""
        assert issubclass(subclass, StreamblocksError)


class TestAdapterNotConfiguredError:
    """Tests for AdapterNotConfiguredError."""

    def test_message_and_attribute(self) -> None:
        """The context is stored and rendered in the message."""
        error = AdapterNotConfiguredError(context="process_chunk")

        assert error.context == "process_chunk"
        assert "process_chunk" in str(error)
        assert "internal state error" in str(error)

    def test_catchable_as_base(self) -> None:
        """It can be caught via the base class."""
        with pytest.raises(StreamblocksError):
            raise AdapterNotConfiguredError(context="process_stream")


class TestAdapterDetectionError:
    """Tests for AdapterDetectionError."""

    def test_message_and_attributes(self) -> None:
        """Chunk type and registered prefixes are stored and rendered."""
        error = AdapterDetectionError(
            chunk_type="openai.types.ChatCompletionChunk",
            registered_prefixes=("anthropic", "google"),
        )

        assert error.chunk_type == "openai.types.ChatCompletionChunk"
        assert error.registered_prefixes == ("anthropic", "google")
        assert "openai.types.ChatCompletionChunk" in str(error)
        assert "anthropic" in str(error)


class TestSyntaxConfigError:
    """Tests for SyntaxConfigError."""

    def test_message_and_attribute(self) -> None:
        """The received type name is stored and rendered."""
        error = SyntaxConfigError(received_type="str")

        assert error.received_type == "str"
        assert "str" in str(error)
        assert "Syntax enum" in str(error)
