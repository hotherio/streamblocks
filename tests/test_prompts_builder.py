"""Tests for prompt builder helpers and Registry prompt generation."""

from __future__ import annotations

from typing import Literal

from hother.streamblocks.core.models import Block
from hother.streamblocks.core.parsing import parse_as_yaml
from hother.streamblocks.core.registry import Registry
from hother.streamblocks.core.types import BaseContent, BaseMetadata
from hother.streamblocks.prompts.builder import (
    build_block_context,
    extract_schema,
    filter_schema_fields,
    generate_block_prompt,
    infer_block_type_name,
)
from hother.streamblocks.syntaxes.delimiter import DelimiterFrontmatterSyntax, DelimiterPreambleSyntax


class GreetMeta(BaseMetadata):
    block_type: Literal["greet"] = "greet"
    tone: str | None = None


@parse_as_yaml()
class GreetContent(BaseContent):
    name: str = ""


class Greet(Block[GreetMeta, GreetContent]):
    """Greet someone.

    Use this block to greet a person by name.
    """

    __examples__ = [
        {"metadata": {"id": "g1", "block_type": "greet", "tone": "warm"}, "content": {"name": "Ada"}},
    ]


class NoDefaultMeta(BaseMetadata):
    block_type: str


class CamelCaseThing(Block[NoDefaultMeta, BaseContent]):
    """A block whose type name is inferred from the class name."""


def test_infer_block_type_from_declared_default() -> None:
    assert infer_block_type_name(Greet) == "greet"


def test_infer_block_type_snake_case_fallback() -> None:
    assert infer_block_type_name(CamelCaseThing) == "camel_case_thing"


def test_build_block_context_includes_examples_and_format() -> None:
    context = build_block_context(Greet, DelimiterPreambleSyntax())
    assert context["name"] == "greet"
    assert context["description"] == "Greet someone."
    assert context["usage"] == "Use this block to greet a person by name."
    assert context["content_format"] is not None
    assert context["metadata_schema"]["properties"].keys() == {"tone"}
    assert context["examples"] == ["!!g1:greet\nname: Ada\n!!end"]


def test_build_block_context_without_examples() -> None:
    context = build_block_context(Greet, DelimiterPreambleSyntax(), include_examples=False)
    assert context["examples"] == []


def test_build_block_context_description_override() -> None:
    context = build_block_context(Greet, DelimiterPreambleSyntax(), description="Custom.")
    assert context["description"] == "Custom."


def test_generate_block_prompt_single() -> None:
    prompt = generate_block_prompt(Greet, DelimiterPreambleSyntax())
    assert "# greet Block" in prompt
    assert "Delimiter Preamble Syntax" in prompt
    assert "!!g1:greet" in prompt


def test_extract_schema_excludes_base_fields() -> None:
    schema = extract_schema(GreetMeta, "metadata")
    assert "id" not in schema["properties"]
    assert "block_type" not in schema["properties"]
    assert "tone" in schema["properties"]


def test_extract_schema_with_extra_excludes() -> None:
    schema = extract_schema(GreetMeta, "metadata", exclude_fields={"tone"})
    assert schema["properties"] == {}


def test_filter_schema_without_properties_returns_input() -> None:
    schema = {"type": "object"}
    assert filter_schema_fields(schema, "metadata") == {"type": "object"}


def test_filter_schema_without_required_key() -> None:
    result = filter_schema_fields({"properties": {"a": {}, "id": {}}}, "metadata")
    assert result["properties"] == {"a": {}}
    assert "required" not in result


def test_filter_schema_filters_required_list() -> None:
    schema = {
        "properties": {"id": {}, "block_type": {}, "tone": {}},
        "required": ["id", "block_type", "tone"],
    }
    result = filter_schema_fields(schema, "metadata")
    assert result["properties"] == {"tone": {}}
    assert result["required"] == ["tone"]


def test_registry_to_prompt_lists_blocks() -> None:
    registry = Registry(syntax=DelimiterFrontmatterSyntax())
    registry.register("greet", Greet)
    prompt = registry.to_prompt()
    assert "## Available Block Types" in prompt
    assert "### greet" in prompt
    assert "Delimiter Frontmatter Syntax" in prompt


def test_registry_registered_blocks_is_readonly_view() -> None:
    registry = Registry()
    registry.register("greet", Greet)
    blocks = registry.registered_blocks
    assert dict(blocks) == {"greet": Greet}


def test_registry_serialize_block() -> None:
    registry = Registry(syntax=DelimiterPreambleSyntax())
    block = Greet.get_examples()[0]
    assert registry.serialize_block(block) == "!!g1:greet\nname: Ada\n!!end"


def test_registry_custom_template() -> None:
    registry = Registry(syntax=DelimiterPreambleSyntax())
    registry.register("greet", Greet)
    registry.register_template("concise", "BLOCKS: {{ blocks | length }}", mode="registry")
    assert registry.to_prompt(template_version="concise") == "BLOCKS: 1"
