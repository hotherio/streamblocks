"""Tests for the Block examples mechanism (inline, dynamic, and file-based)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import pytest

from hother.streamblocks.core.models import Block
from hother.streamblocks.core.parsing import parse_as_yaml
from hother.streamblocks.core.types import BaseContent, BaseMetadata

if TYPE_CHECKING:
    from pathlib import Path


class GreetMeta(BaseMetadata):
    block_type: Literal["greet"] = "greet"


@parse_as_yaml()
class GreetContent(BaseContent):
    name: str = ""


class PlainContent(BaseContent):
    pass


def _make_block_class() -> type[Block[GreetMeta, GreetContent]]:
    """A fresh Greet subclass so example caches/storage don't leak across tests."""

    class Greet(Block[GreetMeta, GreetContent]):
        """Greet someone."""

    return Greet


def test_inline_example_autofills_yaml_raw_content() -> None:
    block_cls = _make_block_class()
    block_cls.__examples__ = [{"metadata": {"id": "g1", "block_type": "greet"}, "content": {"name": "Ada"}}]
    examples = block_cls.get_examples()
    assert len(examples) == 1
    assert examples[0].content.raw_content == "name: Ada"


def test_inline_example_autofills_json_raw_content() -> None:
    class JsonMeta(BaseMetadata):
        block_type: Literal["plain"] = "plain"

    class PlainBlock(Block[JsonMeta, PlainContent]):
        """Plain block (defaults to JSON serialization)."""

    PlainBlock.__examples__ = [{"metadata": {"id": "p1", "block_type": "plain"}, "content": {"value": "hi"}}]
    assert PlainBlock.get_examples()[0].content.raw_content == '{"value": "hi"}'


def test_inline_example_honors_explicit_raw_content() -> None:
    block_cls = _make_block_class()
    block_cls.__examples__ = [
        {"metadata": {"id": "g1", "block_type": "greet"}, "content": {"name": "Ada", "raw_content": "custom"}},
    ]
    assert block_cls.get_examples()[0].content.raw_content == "custom"


def test_add_example_dict_and_instance() -> None:
    block_cls = _make_block_class()
    block_cls.add_example({"metadata": {"id": "d1", "block_type": "greet"}, "content": {"name": "Bo"}})
    block_cls.add_example(block_cls(metadata=GreetMeta(id="d2"), content=GreetContent(raw_content="x")))
    assert {ex.metadata.id for ex in block_cls.get_examples()} == {"d1", "d2"}


def test_add_examples_and_clear() -> None:
    block_cls = _make_block_class()
    block_cls.add_examples(
        [
            {"metadata": {"id": "a", "block_type": "greet"}, "content": {"name": "A"}},
            {"metadata": {"id": "b", "block_type": "greet"}, "content": {"name": "B"}},
        ]
    )
    assert len(block_cls.get_examples()) == 2
    block_cls.clear_examples()
    assert block_cls.get_examples() == []


def test_add_example_with_content_instance_skips_autofill() -> None:
    block_cls = _make_block_class()
    block_cls.add_example({"metadata": {"id": "i1", "block_type": "greet"}, "content": GreetContent(raw_content="rc")})
    assert block_cls.get_examples()[0].content.raw_content == "rc"


_FILE_HEADER = "---\nsyntax: DELIMITER_FRONTMATTER\n---\n\n"
_VALID_BLOCK = "!!start\n---\nid: ex1\nblock_type: greet\n---\nname: Bob\n!!end\n"


def _write(tmp_path: Path, body: str, name: str = "examples.md") -> Path:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


def test_file_examples_load_and_cache(tmp_path: Path) -> None:
    block_cls = _make_block_class()
    block_cls.__examples__ = _write(tmp_path, _FILE_HEADER + _VALID_BLOCK)
    first = block_cls.get_examples()
    second = block_cls.get_examples()  # second call hits the mtime cache
    assert first[0].metadata.id == "ex1"
    assert first[0].content.name == "Bob"
    assert [e.metadata.id for e in second] == ["ex1"]


def test_file_examples_with_leading_prose(tmp_path: Path) -> None:
    block_cls = _make_block_class()
    body = _FILE_HEADER + "Some intro prose before the block.\n\n" + _VALID_BLOCK
    block_cls.__examples__ = _write(tmp_path, body)
    assert block_cls.get_examples()[0].metadata.id == "ex1"


def test_file_examples_as_string_path(tmp_path: Path) -> None:
    block_cls = _make_block_class()
    block_cls.__examples__ = str(_write(tmp_path, _FILE_HEADER + _VALID_BLOCK))
    assert block_cls.get_examples()[0].metadata.id == "ex1"


def test_file_examples_missing_file() -> None:
    block_cls = _make_block_class()
    block_cls.__examples__ = "/nonexistent/path/examples.md"
    with pytest.raises(FileNotFoundError):
        block_cls.get_examples()


def test_file_examples_no_frontmatter(tmp_path: Path) -> None:
    block_cls = _make_block_class()
    block_cls.__examples__ = _write(tmp_path, "no frontmatter here")
    with pytest.raises(ValueError, match="must start with YAML frontmatter"):
        block_cls.get_examples()


def test_file_examples_incomplete_frontmatter(tmp_path: Path) -> None:
    block_cls = _make_block_class()
    block_cls.__examples__ = _write(tmp_path, "---\nsyntax: DELIMITER_FRONTMATTER\n")
    with pytest.raises(ValueError, match="Invalid frontmatter"):
        block_cls.get_examples()


def test_file_examples_non_mapping_frontmatter(tmp_path: Path) -> None:
    block_cls = _make_block_class()
    block_cls.__examples__ = _write(tmp_path, "---\n- just\n- a list\n---\nbody")
    with pytest.raises(TypeError, match="must be a YAML mapping"):
        block_cls.get_examples()


def test_file_examples_non_string_syntax(tmp_path: Path) -> None:
    block_cls = _make_block_class()
    block_cls.__examples__ = _write(tmp_path, "---\nsyntax: 123\n---\nbody")
    with pytest.raises(TypeError, match="name a string 'syntax' field"):
        block_cls.get_examples()


def test_file_examples_unknown_syntax(tmp_path: Path) -> None:
    block_cls = _make_block_class()
    block_cls.__examples__ = _write(tmp_path, "---\nsyntax: NOPE\n---\nbody")
    with pytest.raises(ValueError, match="Unknown syntax"):
        block_cls.get_examples()


def test_file_examples_unparseable_block_raises(tmp_path: Path) -> None:
    block_cls = _make_block_class()
    bad_block = "!!start\n---\nblock_type: greet\n---\nname: Bob\n!!end\n"  # missing required id
    block_cls.__examples__ = _write(tmp_path, _FILE_HEADER + bad_block)
    with pytest.raises(ValueError, match="Failed to parse example block"):
        block_cls.get_examples()
