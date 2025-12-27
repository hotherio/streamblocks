"""Tests for memory block models."""

from __future__ import annotations

from typing import Literal

import pytest
from pydantic import ValidationError

from hother.streamblocks_examples.blocks.agent.memory import Memory, MemoryContent, MemoryMetadata


class TestMemoryMetadata:
    """Tests for MemoryMetadata model."""

    def test_metadata_with_required_fields(self) -> None:
        """Test creating metadata with required fields."""
        metadata = MemoryMetadata(
            id="mem-1",
            block_type="memory",
            memory_type="store",
            key="test_key",
        )

        assert metadata.id == "mem-1"
        assert metadata.block_type == "memory"
        assert metadata.memory_type == "store"
        assert metadata.key == "test_key"
        assert metadata.ttl_seconds is None
        assert metadata.namespace == "default"

    def test_metadata_with_all_fields(self) -> None:
        """Test creating metadata with all fields."""
        metadata = MemoryMetadata(
            id="mem-2",
            block_type="memory",
            memory_type="recall",
            key="user_preferences",
            ttl_seconds=3600,
            namespace="user_data",
        )

        assert metadata.memory_type == "recall"
        assert metadata.key == "user_preferences"
        assert metadata.ttl_seconds == 3600
        assert metadata.namespace == "user_data"

    @pytest.mark.parametrize(
        "memory_type",
        ["store", "recall", "update", "delete", "list"],
    )
    def test_metadata_valid_memory_types(
        self, memory_type: Literal["store", "recall", "update", "delete", "list"]
    ) -> None:
        """Test all valid memory_type values."""
        metadata = MemoryMetadata(
            id="mem-3",
            block_type="memory",
            memory_type=memory_type,
            key="test",
        )

        assert metadata.memory_type == memory_type

    def test_metadata_invalid_memory_type(self) -> None:
        """Test that invalid memory_type raises error."""
        with pytest.raises(ValidationError):
            MemoryMetadata(
                id="mem-4",
                block_type="memory",
                memory_type="invalid",  # type: ignore[arg-type]
                key="test",
            )

    def test_metadata_missing_required_field(self) -> None:
        """Test that missing required fields raise error."""
        with pytest.raises(ValidationError):
            MemoryMetadata(
                id="mem-5",
                block_type="memory",
                memory_type="store",
                # Missing key
            )  # type: ignore[call-arg]


class TestMemoryContentParse:
    """Tests for MemoryContent.parse() method."""

    def test_parse_empty_raw_text(self) -> None:
        """Test parsing empty raw_text returns content with raw_content only."""
        content = MemoryContent.parse("")

        assert content.raw_content == ""
        assert content.value is None
        assert content.previous_value is None
        assert content.keys is None

    def test_parse_whitespace_only(self) -> None:
        """Test parsing whitespace-only text returns content with raw_content only."""
        content = MemoryContent.parse("   \n\t  ")

        assert content.raw_content == "   \n\t  "
        assert content.value is None

    def test_parse_yaml_with_value_key(self) -> None:
        """Test parsing YAML dict with 'value' key extracts value."""
        yaml_text = "value: test_value"
        content = MemoryContent.parse(yaml_text)

        assert content.raw_content == yaml_text
        assert content.value == "test_value"

    def test_parse_yaml_with_value_and_other_keys(self) -> None:
        """Test parsing YAML with value and additional keys."""
        yaml_text = "value: important_data\nprevious_value: old_data"
        content = MemoryContent.parse(yaml_text)

        assert content.value == "important_data"
        assert content.previous_value == "old_data"

    def test_parse_yaml_with_keys_list(self) -> None:
        """Test parsing YAML with keys list for list operations.

        Note: The parse() method only extracts fields when 'value' key is present,
        otherwise it treats entire dict as the value.
        """
        yaml_text = "keys:\n  - key1\n  - key2\n  - key3"
        content = MemoryContent.parse(yaml_text)

        # Without 'value' key, the entire dict becomes the value
        assert content.value == {"keys": ["key1", "key2", "key3"]}
        assert content.keys is None  # Not extracted since no 'value' key

    def test_parse_yaml_dict_without_value_key(self) -> None:
        """Test parsing YAML dict without 'value' key treats entire dict as value."""
        yaml_text = "name: John\nage: 30"
        content = MemoryContent.parse(yaml_text)

        assert content.raw_content == yaml_text
        assert content.value == {"name": "John", "age": 30}

    def test_parse_yaml_scalar_raises_type_error(self) -> None:
        """Test parsing YAML scalar raises TypeError.

        Note: The code expects YAML to be a dict, so scalar values cause
        a TypeError when checking 'value' in data. This is only caught
        if it's a yaml.YAMLError, so TypeError propagates.
        """
        yaml_text = "42"
        with pytest.raises(TypeError, match="not iterable"):
            MemoryContent.parse(yaml_text)

    def test_parse_yaml_list_becomes_value(self) -> None:
        """Test parsing YAML list becomes value.

        Note: 'value' in list checks if 'value' is an element, which is False,
        so the code treats the entire list as the value.
        """
        yaml_text = "- item1\n- item2\n- item3"
        content = MemoryContent.parse(yaml_text)

        assert content.value == ["item1", "item2", "item3"]

    def test_parse_yaml_quoted_string_becomes_value(self) -> None:
        """Test parsing YAML quoted string becomes value.

        Note: 'value' in string checks if 'value' is a substring, which is False,
        so the code treats the entire string as the value.
        """
        yaml_text = '"hello world"'
        content = MemoryContent.parse(yaml_text)

        assert content.value == "hello world"

    def test_parse_yaml_nested_dict(self) -> None:
        """Test parsing nested YAML dict."""
        yaml_text = "user:\n  name: Alice\n  settings:\n    theme: dark"
        content = MemoryContent.parse(yaml_text)

        assert content.value == {
            "user": {
                "name": "Alice",
                "settings": {"theme": "dark"},
            }
        }

    def test_parse_invalid_yaml_fallback_to_plain_text(self) -> None:
        """Test parsing invalid YAML falls back to plain text value."""
        invalid_yaml = "key: value: invalid: nested: colons"
        content = MemoryContent.parse(invalid_yaml)

        assert content.raw_content == invalid_yaml
        assert content.value == invalid_yaml.strip()

    def test_parse_yaml_error_fallback(self) -> None:
        """Test YAML parse error falls back to plain text."""
        # This is invalid YAML due to unmatched bracket
        invalid_yaml = "[unclosed bracket"
        content = MemoryContent.parse(invalid_yaml)

        assert content.raw_content == invalid_yaml
        assert content.value == invalid_yaml.strip()

    def test_parse_yaml_null_becomes_empty_dict(self) -> None:
        """Test parsing YAML null or empty returns empty content."""
        # YAML null/empty returns None, which is treated as empty dict
        content = MemoryContent.parse("null")

        # yaml.safe_load("null") returns None
        # {} or {} gives {} so value should be {} (empty dict since data is None/empty)
        assert content.raw_content == "null"
        # Note: yaml.safe_load("null") returns None, so data becomes {}
        assert content.value is None or content.value == {}

    def test_parse_complex_value_with_all_fields(self) -> None:
        """Test parsing complex YAML with value, previous_value, and keys."""
        yaml_text = """
value:
  name: test
  count: 5
previous_value:
  name: old
keys:
  - a
  - b
"""
        content = MemoryContent.parse(yaml_text)

        assert content.value == {"name": "test", "count": 5}
        assert content.previous_value == {"name": "old"}
        assert content.keys == ["a", "b"]


class TestMemoryContentModel:
    """Tests for MemoryContent model validation."""

    def test_content_default_values(self) -> None:
        """Test content with default values."""
        content = MemoryContent(raw_content="test")

        assert content.raw_content == "test"
        assert content.value is None
        assert content.previous_value is None
        assert content.keys is None

    def test_content_with_all_values(self) -> None:
        """Test content with all values set."""
        content = MemoryContent(
            raw_content="original",
            value={"key": "value"},
            previous_value={"key": "old_value"},
            keys=["key1", "key2"],
        )

        assert content.value == {"key": "value"}
        assert content.previous_value == {"key": "old_value"}
        assert content.keys == ["key1", "key2"]


class TestMemoryBlockType:
    """Tests for Memory block type alias."""

    def test_memory_type_alias_exists(self) -> None:
        """Test that Memory type alias is available."""
        # Memory is an alias for Block[MemoryMetadata, MemoryContent]
        # We can verify it exists by checking it's not None
        assert Memory is not None

    def test_memory_can_be_created(self) -> None:
        """Test that Memory block can be created with proper types."""
        metadata = MemoryMetadata(
            id="test-mem",
            block_type="memory",
            memory_type="store",
            key="test_key",
        )
        content = MemoryContent(raw_content="test_value", value="test_value")

        block = Memory(metadata=metadata, content=content)

        assert block.metadata.memory_type == "store"
        assert block.content.value == "test_value"
