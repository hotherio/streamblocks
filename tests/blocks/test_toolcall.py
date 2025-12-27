"""Tests for tool calling block models."""

from __future__ import annotations

import pytest

from hother.streamblocks_examples.blocks.agent.toolcall import ToolCallContent, ToolCallMetadata


class TestToolCallMetadata:
    """Tests for ToolCallMetadata model."""

    def test_create_metadata(self) -> None:
        """Test creating tool call metadata."""
        metadata = ToolCallMetadata(
            block_type="tool_call",
            id="test-1",
            tool_name="my_tool",
        )
        assert metadata.tool_name == "my_tool"
        assert metadata.async_call is False
        assert metadata.timeout is None

    def test_metadata_with_options(self) -> None:
        """Test metadata with optional fields."""
        metadata = ToolCallMetadata(
            block_type="tool_call",
            id="test-2",
            tool_name="async_tool",
            async_call=True,
            timeout=30.0,
            description="Test tool",
        )
        assert metadata.async_call is True
        assert metadata.timeout == 30.0
        assert metadata.description == "Test tool"


class TestToolCallContentParse:
    """Tests for ToolCallContent.parse()."""

    def test_parse_valid_yaml(self) -> None:
        """Test parsing valid YAML parameters."""
        raw = "key: value\nnumber: 42"
        content = ToolCallContent.parse(raw)
        assert content.parameters == {"key": "value", "number": 42}
        assert content.raw_content == raw

    def test_parse_nested_yaml(self) -> None:
        """Test parsing nested YAML structure."""
        raw = "outer:\n  inner: value\n  list:\n    - one\n    - two"
        content = ToolCallContent.parse(raw)
        assert content.parameters["outer"]["inner"] == "value"
        assert content.parameters["outer"]["list"] == ["one", "two"]

    def test_parse_empty_yaml(self) -> None:
        """Test parsing empty YAML returns empty dict."""
        content = ToolCallContent.parse("")
        assert content.parameters == {}

    def test_parse_null_yaml(self) -> None:
        """Test parsing null YAML returns empty dict."""
        content = ToolCallContent.parse("null")
        assert content.parameters == {}

    def test_parse_invalid_yaml_raises_error(self) -> None:
        """Test that invalid YAML raises ValueError.

        This covers lines 31-37.
        """
        with pytest.raises(ValueError, match="Invalid YAML parameters"):
            ToolCallContent.parse("[unclosed: bracket")

    def test_parse_invalid_yaml_multiline(self) -> None:
        """Test invalid YAML across multiple lines."""
        raw = "key: [value\nunclosed: true"
        with pytest.raises(ValueError, match="Invalid YAML"):
            ToolCallContent.parse(raw)

    def test_parse_yaml_list(self) -> None:
        """Test parsing YAML list."""
        raw = "items:\n  - one\n  - two\n  - three"
        content = ToolCallContent.parse(raw)
        assert content.parameters["items"] == ["one", "two", "three"]

    def test_parse_preserves_types(self) -> None:
        """Test that YAML types are preserved."""
        raw = "string: hello\nint: 42\nfloat: 3.14\nbool: true"
        content = ToolCallContent.parse(raw)
        assert content.parameters["string"] == "hello"
        assert content.parameters["int"] == 42
        assert content.parameters["float"] == 3.14
        assert content.parameters["bool"] is True
