"""Edge paths of the artifact blocks, the XML syntax, the grammar and the guarded stream."""

from __future__ import annotations

from typing import Self

import pytest
from pydantic import ValidationError

from hother.streamblocks import (
    DelimiterFrontmatterSyntax,
    DelimiterPreambleSyntax,
    Registry,
    StreamBlockProcessor,
    XmlTagSyntax,
)
from hother.streamblocks.blocks.artifacts import ARTIFACT_BLOCKS, PatchArtifact, PatchArtifactContent
from hother.streamblocks.core import utils
from hother.streamblocks.core.models import Block, BlockCandidate
from hother.streamblocks.core.processor import ProcessorConfig
from hother.streamblocks.core.types import BaseContent, BaseMetadata, BlockErrorCode, BlockErrorEvent
from hother.streamblocks.grammar import FieldKind, GrammarError, accepts, build_grammar, render_gbnf
from hother.streamblocks.grammar.nodes import ROOT_RULE, CharSet, Grammar, Repeat, without_line_break
from hother.streamblocks.grammar.spec import block_spec
from hother.streamblocks.guards import path_within

HUNK = "<<<<<<< SEARCH\na\n=======\nb\n>>>>>>> REPLACE"
OPENING = '<artifact type="patch" id="p" path="src/a.py">'
CLOSING = "</artifact>"
BAD = '<artifact type="file" id="bad" path="../secrets.env">\nTOKEN = 1\n</artifact>\n'
LOWER, UPPER = 2, 3


def _candidate(*lines: str) -> BlockCandidate:
    candidate = BlockCandidate(XmlTagSyntax(), start_line=1)
    candidate.lines.extend(lines)
    return candidate


def test_patch_content_accepts_explicit_hunks_and_instances() -> None:
    parsed = PatchArtifactContent.parse(HUNK)
    explicit = PatchArtifactContent(raw_content="ignored", hunks=parsed.hunks)

    assert explicit.hunks == parsed.hunks
    assert PatchArtifactContent.model_validate(parsed) == parsed
    with pytest.raises(ValidationError):
        PatchArtifactContent.model_validate(HUNK)


def test_xml_parse_block_reports_bad_opening_and_bad_content() -> None:
    syntax = XmlTagSyntax()

    missing = syntax.parse_block(_candidate(), PatchArtifact)
    assert not missing.success
    assert missing.error == "Missing or invalid opening tag"

    broken = syntax.parse_block(_candidate(OPENING, "not a hunk", CLOSING), PatchArtifact)
    assert not broken.success

    assert syntax.parse_block(_candidate(OPENING, HUNK, CLOSING), PatchArtifact).success


def test_xml_early_content_needs_both_tags() -> None:
    syntax = XmlTagSyntax()

    assert syntax.parse_content_early(_candidate(OPENING)) is None
    assert syntax.parse_content_early(_candidate(OPENING, "x", CLOSING)) == {"raw_content": "x"}


class _PlainStream:
    """An async iterator with no ``aclose``, unlike an async generator."""

    def __init__(self, text: str) -> None:
        self._lines = iter(text.splitlines(keepends=True))

    def __aiter__(self) -> Self:
        return self

    async def __anext__(self) -> str:
        try:
            return next(self._lines)
        except StopIteration:
            raise StopAsyncIteration from None


@pytest.mark.asyncio
async def test_abort_works_on_a_stream_that_cannot_be_closed() -> None:
    registry = Registry(syntax=XmlTagSyntax(), blocks=ARTIFACT_BLOCKS)
    registry.add_stream_validator(path_within("src"))
    processor = StreamBlockProcessor(registry, ProcessorConfig(abort_stream_on_failure=True))

    events = [event async for event in processor.process_stream(_PlainStream(BAD))]

    assert [e.error_code for e in events if isinstance(e, BlockErrorEvent)] == [BlockErrorCode.ABORTED]
    assert processor.aborted


def test_load_yaml_without_libyaml(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(utils.yaml, "__with_libyaml__", False)

    assert utils.load_yaml("a: 1\nb: [x, y]\n") == {"a": 1, "b": ["x", "y"]}


class MixedMetadata(BaseMetadata):
    """Metadata with a field of two possible types."""

    level: int | str = 0


class Mixed(Block[MixedMetadata, BaseContent]):
    """A block whose metadata the grammar cannot type."""


@pytest.mark.parametrize("syntax", [XmlTagSyntax(), DelimiterFrontmatterSyntax()])
def test_field_of_several_types_is_left_untyped(syntax: XmlTagSyntax | DelimiterFrontmatterSyntax) -> None:
    (level,) = block_spec("mixed", Mixed).fields
    assert level.kind is FieldKind.ANY

    registry = Registry(syntax=syntax, blocks={"mixed": Mixed})
    block = Mixed(
        metadata=MixedMetadata(id="m", block_type="mixed", level="high"), content=BaseContent(raw_content="x")
    )
    assert accepts(build_grammar(registry), registry.serialize_block(block) + "\n")


def test_preamble_rejects_block_types_it_cannot_write() -> None:
    registry = Registry(syntax=DelimiterPreambleSyntax(), blocks={"my-note": Mixed})

    with pytest.raises(GrammarError, match="cannot be written in a preamble"):
        registry.to_grammar()


def test_bounded_repetition_renders_as_a_range() -> None:
    letter = CharSet(ranges=(("a", "z"),))
    grammar = Grammar(rules={ROOT_RULE: Repeat(letter, LOWER, UPPER)})

    assert render_gbnf(grammar) == "root ::= [a-z]{2,3}\n"
    assert (
        Registry(syntax=XmlTagSyntax(), blocks=ARTIFACT_BLOCKS)
        .to_grammar(allow_text=False, min_blocks=LOWER)
        .startswith("root ::= block{2,}\n")
    )


def test_without_line_break_needs_a_terminated_line() -> None:
    with pytest.raises(ValueError, match="line break"):
        without_line_break(CharSet(chars="a"))
