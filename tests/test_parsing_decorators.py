"""Tests for parsing decorators."""

import json
from typing import Any

import pytest
import yaml
from pydantic import Field, ValidationError

from hother.streamblocks import ParseStrategy, parse_as_json, parse_as_yaml
from hother.streamblocks.core.models import BaseContent


# Test models
@parse_as_yaml()
class YAMLTestContent(BaseContent):
    """Test content that parses from YAML."""

    name: str = ""
    value: int = 0
    tags: list[str] = Field(default_factory=list)


@parse_as_yaml(strategy=ParseStrategy.STRICT)
class StrictYAMLContent(BaseContent):
    """Test content with strict YAML parsing."""

    required_field: str = ""


@parse_as_json()
class JSONTestContent(BaseContent):
    """Test content that parses from JSON."""

    status: int = 0
    data: dict[str, Any] = Field(default_factory=dict)


@parse_as_json(strategy=ParseStrategy.STRICT)
class StrictJSONContent(BaseContent):
    """Test content with strict JSON parsing."""

    id: str = ""
    count: int = 0


# YAML Parsing Tests


def test_parse_as_yaml_valid() -> None:
    """Test parsing valid YAML."""
    yaml_text = """
name: test
value: 42
tags:
  - foo
  - bar
"""
    content = YAMLTestContent.parse(yaml_text)
    assert content.name == "test"
    assert content.value == 42
    assert content.tags == ["foo", "bar"]
    assert content.raw_content == yaml_text


def test_parse_as_yaml_empty() -> None:
    """Test parsing empty YAML."""
    content = YAMLTestContent.parse("")
    assert content.raw_content == ""


def test_parse_as_yaml_permissive_invalid() -> None:
    """Test PERMISSIVE strategy falls back on invalid YAML."""
    invalid_yaml = "name: test\n  invalid: [unclosed"

    # Should not raise, should fall back to raw_content
    content = YAMLTestContent.parse(invalid_yaml)
    assert content.raw_content == invalid_yaml


def test_parse_as_yaml_strict_invalid() -> None:
    """Test STRICT strategy raises on invalid YAML."""
    invalid_yaml = "name: test\n  invalid: [unclosed"

    with pytest.raises(yaml.YAMLError):
        StrictYAMLContent.parse(invalid_yaml)


def test_parse_as_yaml_non_dict_wrapped() -> None:
    """Test non-dict YAML values are wrapped in {value: ...}."""

    @parse_as_yaml()
    class SimpleContent(BaseContent):
        value: str

    content = SimpleContent.parse("just a string")
    assert content.value == "just a string"


def test_parse_as_yaml_non_dict_no_wrap() -> None:
    """Test non-dict handling can be disabled."""

    @parse_as_yaml(handle_non_dict=False)
    class NoWrapContent(BaseContent):
        pass

    # With handle_non_dict=False, non-dict values will cause TypeError
    # which falls back to raw_content in PERMISSIVE mode
    content = NoWrapContent.parse("just a string")
    assert content.raw_content == "just a string"


def test_parse_as_yaml_validation_error_permissive() -> None:
    """Test PERMISSIVE strategy handles Pydantic validation errors."""

    @parse_as_yaml()
    class TypedContent(BaseContent):
        number: int = 0

    # Valid YAML but wrong type
    content = TypedContent.parse("number: not_a_number")
    # Should fall back to raw_content instead of raising
    assert content.raw_content == "number: not_a_number"


def test_parse_as_yaml_validation_error_strict() -> None:
    """Test STRICT strategy raises on Pydantic validation errors."""

    @parse_as_yaml(strategy=ParseStrategy.STRICT)
    class StrictTypedContent(BaseContent):
        number: int = 0

    # Valid YAML but wrong type
    with pytest.raises((ValidationError, TypeError)):
        StrictTypedContent.parse("number: not_a_number")


# JSON Parsing Tests


def test_parse_as_json_valid() -> None:
    """Test parsing valid JSON."""
    json_text = '{"status": 200, "data": {"key": "value"}}'

    content = JSONTestContent.parse(json_text)
    assert content.status == 200
    assert content.data == {"key": "value"}
    assert content.raw_content == json_text


def test_parse_as_json_empty() -> None:
    """Test parsing empty JSON."""
    content = JSONTestContent.parse("")
    assert content.raw_content == ""


def test_parse_as_json_permissive_invalid() -> None:
    """Test PERMISSIVE strategy falls back on invalid JSON."""
    invalid_json = '{"status": 200, "data": {'

    # Should not raise, should fall back to raw_content
    content = JSONTestContent.parse(invalid_json)
    assert content.raw_content == invalid_json


def test_parse_as_json_strict_invalid() -> None:
    """Test STRICT strategy raises on invalid JSON."""
    invalid_json = '{"id": "test", "count": }'

    with pytest.raises(json.JSONDecodeError):
        StrictJSONContent.parse(invalid_json)


def test_parse_as_json_non_dict_wrapped() -> None:
    """Test non-dict JSON values are wrapped in {value: ...}."""

    @parse_as_json()
    class SimpleJSONContent(BaseContent):
        value: str

    content = SimpleJSONContent.parse('"just a string"')
    assert content.value == "just a string"


def test_parse_as_json_non_dict_no_wrap() -> None:
    """Test non-dict handling can be disabled."""

    @parse_as_json(handle_non_dict=False)
    class NoWrapJSONContent(BaseContent):
        pass

    # With handle_non_dict=False, non-dict values will cause TypeError
    # which falls back to raw_content in PERMISSIVE mode
    content = NoWrapJSONContent.parse('"just a string"')
    assert content.raw_content == '"just a string"'


def test_parse_as_json_validation_error_permissive() -> None:
    """Test PERMISSIVE strategy handles Pydantic validation errors."""

    @parse_as_json()
    class TypedJSONContent(BaseContent):
        number: int = 0

    # Valid JSON but wrong type
    content = TypedJSONContent.parse('{"number": "not_a_number"}')
    # Should fall back to raw_content instead of raising
    assert content.raw_content == '{"number": "not_a_number"}'


def test_parse_as_json_validation_error_strict() -> None:
    """Test STRICT strategy raises on Pydantic validation errors."""

    @parse_as_json(strategy=ParseStrategy.STRICT)
    class StrictTypedJSONContent(BaseContent):
        number: int = 0

    # Valid JSON but wrong type
    with pytest.raises((ValidationError, TypeError)):
        StrictTypedJSONContent.parse('{"number": "not_a_number"}')


# Integration Tests


def test_decorator_inheritance() -> None:
    """Test that decorators don't break inheritance."""

    @parse_as_yaml()
    class ParentContent(BaseContent):
        base_field: str

    @parse_as_yaml()
    class ChildContent(ParentContent):
        child_field: int

    yaml_text = """
base_field: parent
child_field: 42
"""
    content = ChildContent.parse(yaml_text)
    assert content.base_field == "parent"
    assert content.child_field == 42


def test_multiple_instances() -> None:
    """Test parsing multiple instances of same class."""

    @parse_as_yaml()
    class MultiContent(BaseContent):
        name: str

    content1 = MultiContent.parse("name: first")
    content2 = MultiContent.parse("name: second")

    assert content1.name == "first"
    assert content2.name == "second"
    assert content1.raw_content != content2.raw_content
