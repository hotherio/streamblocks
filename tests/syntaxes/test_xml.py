"""Tests for the XML tag syntax."""

from __future__ import annotations

from itertools import pairwise

import pytest
from hypothesis import given, settings, strategies as st

from hother.streamblocks import Registry, StreamBlockProcessor, XmlTagSyntax
from hother.streamblocks.blocks.artifacts import ARTIFACT_BLOCKS, FileArtifact
from hother.streamblocks.core.processor import ProcessorConfig
from hother.streamblocks.core.types import (
    BlockContentDeltaEvent,
    BlockEndEvent,
    BlockErrorCode,
    BlockErrorEvent,
    Event,
    TextContentEvent,
)
from hother.streamblocks.syntaxes import Syntax, get_syntax_instance

STREAM = (
    "Here is the file:\n"
    '<artifact type="file" id="main" path="src/main.py" language="python">\n'
    "def main() -> None:\n"
    '    print("<hello> & goodbye")\n'
    "</artifact>\n"
    "Done.\n"
)


def _run(text: str, cuts: tuple[int, ...] = (), syntax: XmlTagSyntax | None = None) -> list[Event]:
    registry = Registry(syntax=syntax or XmlTagSyntax(), blocks=ARTIFACT_BLOCKS)
    processor = StreamBlockProcessor(registry, ProcessorConfig(emit_text_deltas=False))
    bounds = [0, *sorted(c % (len(text) + 1) for c in cuts), len(text)]
    events = [e for a, b in pairwise(bounds) for e in processor.process_chunk(text[a:b])]
    return [*events, *processor.finalize()]


def _blocks(events: list[Event]) -> list[BlockEndEvent]:
    return [e for e in events if isinstance(e, BlockEndEvent)]


def _texts(events: list[Event]) -> list[str]:
    return [e.content for e in events if isinstance(e, TextContentEvent)]


def test_extracts_typed_file_artifact() -> None:
    events = _run(STREAM)
    (end,) = _blocks(events)
    block = end.get_block()
    assert block is not None
    assert block.metadata.id == "main"
    assert block.metadata.block_type == "file"
    assert block.metadata.path == "src/main.py"
    assert block.metadata.language == "python"
    assert block.content.raw_content == 'def main() -> None:\n    print("<hello> & goodbye")'
    assert _texts(events) == ["Here is the file:", "Done."]


def test_content_lines_are_content_deltas() -> None:
    deltas = [e.delta for e in _run(STREAM) if isinstance(e, BlockContentDeltaEvent)]
    assert deltas == ["def main() -> None:", '    print("<hello> & goodbye")']


def test_attributes_are_unescaped_and_accept_single_quotes() -> None:
    metadata = (
        XmlTagSyntax().detect_line('<artifact type=\'document\' id="d1" title="Tom &amp; &quot;Jerry&quot;">').metadata
    )
    assert metadata == {"id": "d1", "title": 'Tom & "Jerry"', "block_type": "document"}


def test_missing_id_gets_a_stable_generated_id() -> None:
    syntax = XmlTagSyntax()
    line = '<artifact type="file" path="a.py">'
    first = syntax.detect_line(line).metadata
    second = syntax.detect_line(line).metadata
    other = syntax.detect_line('<artifact type="file" path="b.py">').metadata
    assert first is not None
    assert second is not None
    assert other is not None
    assert first["id"] == second["id"]
    assert first["id"].startswith("artifact-")
    assert first["id"] != other["id"]


def test_type_defaults_to_tag_name() -> None:
    metadata = XmlTagSyntax(tag="note").detect_line('<note id="n1">').metadata
    assert metadata == {"id": "n1", "block_type": "note"}


@pytest.mark.parametrize(
    "line",
    [
        "<artifacts>",
        '<artifact type="file"/>',
        'Here: <artifact type="file">',
        '<artifact type="file"> trailing',
        "<other>",
    ],
)
def test_lines_that_do_not_open_a_block(line: str) -> None:
    assert not XmlTagSyntax().detect_line(line).is_opening


def test_text_after_closing_tag_is_reprocessed() -> None:
    events = _run('<artifact type="file" id="a" path="a.py">\nx = 1\n</artifact>And then some prose\n')
    (end,) = _blocks(events)
    assert end.raw_content.splitlines()[-1] == "</artifact>"
    assert _texts(events) == ["And then some prose"]


def test_lenient_close_can_be_disabled() -> None:
    events = _run(
        '<artifact type="file" id="a" path="a.py">\nx = 1\n</artifact>And then\n',
        syntax=XmlTagSyntax(lenient_close=False),
    )
    assert [e.error_code for e in events if isinstance(e, BlockErrorEvent)] == [BlockErrorCode.UNCLOSED_BLOCK]


def test_invalid_metadata_is_rejected() -> None:
    events = _run('<artifact type="file" id="a">\nx = 1\n</artifact>\n')
    assert not _blocks(events)
    assert [e.error_code for e in events if isinstance(e, BlockErrorEvent)] == [BlockErrorCode.PARSE_FAILED]


def test_unregistered_type_falls_back_to_base_models() -> None:
    (end,) = _blocks(_run('<artifact type="sketch" id="s1" color="red">\nlines\n</artifact>\n'))
    assert end.block_type == "sketch"
    assert end.content["raw_content"] == "lines"


def test_serialize_round_trip() -> None:
    syntax = XmlTagSyntax()
    block = FileArtifact.model_validate(
        {
            "metadata": {"id": "m", "block_type": "file", "path": 'a "b".py'},
            "content": {"raw_content": "x = 1\ny = 2"},
        }
    )
    serialized = syntax.serialize_block(block)
    assert serialized.splitlines()[0] == '<artifact type="file" id="m" path="a &quot;b&quot;.py" operation="create">'
    (end,) = _blocks(_run(serialized + "\n"))
    parsed = end.get_block()
    assert parsed is not None
    assert parsed.metadata == block.metadata
    assert parsed.content.raw_content == block.content.raw_content


def test_describe_format_and_registry_prompt() -> None:
    assert "XML Tag Syntax" in XmlTagSyntax().describe_format()
    prompt = Registry(syntax=XmlTagSyntax(), blocks=ARTIFACT_BLOCKS).to_prompt()
    assert '<artifact type="file" id="main" path="src/main.py"' in prompt
    assert "<<<<<<< SEARCH" in prompt


def test_syntax_enum_member() -> None:
    assert isinstance(get_syntax_instance(Syntax.XML_TAG), XmlTagSyntax)


def test_invalid_tag_name_is_rejected() -> None:
    with pytest.raises(ValueError, match="Invalid tag name"):
        XmlTagSyntax(tag="bad tag")


@settings(max_examples=200)
@given(cuts=st.lists(st.integers(min_value=0, max_value=len(STREAM)), max_size=8))
def test_extraction_is_chunking_invariant(cuts: list[int]) -> None:
    reference = _run(STREAM)
    events = _run(STREAM, tuple(cuts))
    assert [e.raw_content for e in _blocks(events)] == [e.raw_content for e in _blocks(reference)]
    assert _texts(events) == _texts(reference)
