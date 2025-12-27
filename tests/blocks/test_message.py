"""Tests for message block models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hother.streamblocks_examples.blocks.agent.message import Message, MessageContent, MessageMetadata


class TestMessageMetadata:
    """Tests for MessageMetadata model."""

    def test_create_metadata_with_required_fields(self) -> None:
        """Test creating metadata with required fields."""
        metadata = MessageMetadata(
            id="msg-1",
            message_type="info",
        )

        assert metadata.id == "msg-1"
        assert metadata.block_type == "message"
        assert metadata.message_type == "info"
        assert metadata.title is None
        assert metadata.priority == "normal"

    def test_all_message_types(self) -> None:
        """Test all valid message types."""
        for msg_type in ["info", "warning", "error", "success", "status", "explanation"]:
            metadata = MessageMetadata(
                id="test",
                message_type=msg_type,  # type: ignore[arg-type]
            )
            assert metadata.message_type == msg_type

    def test_all_priority_levels(self) -> None:
        """Test all valid priority levels."""
        for priority in ["low", "normal", "high"]:
            metadata = MessageMetadata(
                id="test",
                message_type="info",
                priority=priority,  # type: ignore[arg-type]
            )
            assert metadata.priority == priority

    def test_metadata_with_all_fields(self) -> None:
        """Test metadata with all optional fields."""
        metadata = MessageMetadata(
            id="msg-2",
            message_type="warning",
            title="Important Warning",
            priority="high",
        )

        assert metadata.title == "Important Warning"
        assert metadata.priority == "high"

    def test_missing_message_type_raises_error(self) -> None:
        """Test that missing message_type raises validation error."""
        with pytest.raises(ValidationError):
            MessageMetadata(id="msg-3")  # type: ignore[call-arg]


class TestMessageContentParse:
    """Tests for MessageContent.parse()."""

    def test_parse_stores_stripped_text(self) -> None:
        """Test that parse stores stripped raw text.

        This covers line 35 of message.py.
        """
        raw = "  Hello, World!  \n\n"
        content = MessageContent.parse(raw)

        assert content.raw_content == "Hello, World!"

    def test_parse_empty_string(self) -> None:
        """Test parsing empty string."""
        content = MessageContent.parse("")
        assert content.raw_content == ""

    def test_parse_multiline_content(self) -> None:
        """Test parsing multiline content."""
        raw = """
        This is a message
        with multiple lines
        of content.
        """
        content = MessageContent.parse(raw)

        assert "This is a message" in content.raw_content
        assert "multiple lines" in content.raw_content

    def test_parse_preserves_internal_whitespace(self) -> None:
        """Test that internal whitespace is preserved."""
        raw = "Line 1\n\nLine 2"
        content = MessageContent.parse(raw)

        assert "\n\n" in content.raw_content


class TestMessageBlock:
    """Tests for Message block type."""

    def test_message_type_exists(self) -> None:
        """Test that Message type alias is available."""
        assert Message is not None

    def test_create_complete_message(self) -> None:
        """Test creating a complete Message block."""
        metadata = MessageMetadata(
            id="test-msg",
            message_type="success",
            title="Operation Complete",
        )
        content = MessageContent.parse("The operation completed successfully.")

        block = Message(metadata=metadata, content=content)

        assert block.metadata.message_type == "success"
        assert block.metadata.title == "Operation Complete"
        assert "successfully" in block.content.raw_content
