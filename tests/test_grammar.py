"""Tests for grammar export: what the grammar allows, the parser must accept."""

from __future__ import annotations

from random import Random
from typing import Any

import pytest

from hother.streamblocks import (
    BaseContent,
    BaseMetadata,
    Block,
    DelimiterFrontmatterSyntax,
    DelimiterPreambleSyntax,
    MarkdownFrontmatterSyntax,
    Registry,
    StreamBlockProcessor,
    XmlTagSyntax,
)
from hother.streamblocks.blocks.artifacts import ARTIFACT_BLOCKS, FileArtifact
from hother.streamblocks.core.types import BlockEndEvent, BlockErrorEvent, BlockStartEvent, Event
from hother.streamblocks.grammar import GBNF, FieldKind, GrammarError, accepts, build_grammar, render_gbnf, sample
from hother.streamblocks.grammar.nodes import CharSet, Grammar, Ref, choice, line_not_starting_with, optional, seq
from hother.streamblocks.grammar.spec import block_spec

SAMPLES = 300
MIN_BLOCKS = 100
REQUIRED_BLOCKS = 2
SEED = 20261110


class NoteMetadata(BaseMetadata):
    """Metadata with every kind of scalar field."""

    priority: int = 0
    urgent: bool = False
    score: float | None = None


class Note(Block[NoteMetadata, BaseContent]):
    """A note."""


class TaggedMetadata(NoteMetadata):
    """Metadata with a field the grammar cannot type."""

    tags: list[str] | None = None


class Tagged(Block[TaggedMetadata, BaseContent]):
    """A note with tags."""


class ParamMetadata(BaseMetadata):
    """Preamble metadata with positional parameters."""

    param_0: str
    param_1: str | None = None


class Command(Block[ParamMetadata, BaseContent]):
    """A command with positional parameters."""


def _events(registry: Registry, text: str) -> list[Event]:
    processor = StreamBlockProcessor(registry)
    return [*processor.process_chunk(text), *processor.finalize()]


def _assert_round_trip(registry: Registry, *, allow_text: bool = True) -> int:
    """Sample from the grammar and check the parser extracts every block it starts."""
    grammar = build_grammar(registry, allow_text=allow_text)
    rng = Random(SEED)
    extracted = 0
    for _ in range(SAMPLES):
        text = sample(grammar, rng)
        events = _events(registry, text)
        errors = [e.reason for e in events if isinstance(e, BlockErrorEvent)]
        assert not errors, f"{errors}\n---\n{text}"
        started = sum(isinstance(e, BlockStartEvent) for e in events)
        ended = [e for e in events if isinstance(e, BlockEndEvent)]
        assert started == len(ended), text
        assert f"{text}\n".count(_block_marker(registry)) == started, text
        for event in ended:
            assert event.block_type in registry.registered_blocks
            assert event.get_block() is not None
        extracted += len(ended)
    return extracted


def _block_marker(registry: Registry) -> str:
    """A string that appears once per block in sampled text."""
    syntax = registry.syntax
    if isinstance(syntax, XmlTagSyntax):
        return f"</{syntax.tag}>\n"
    if isinstance(syntax, DelimiterFrontmatterSyntax):
        return f"{syntax.end_delimiter}\n"
    assert isinstance(syntax, DelimiterPreambleSyntax)
    return f"{syntax.delimiter}end\n"


@pytest.mark.parametrize("allow_text", [True, False])
def test_xml_artifacts_round_trip(allow_text: bool) -> None:
    registry = Registry(syntax=XmlTagSyntax(), blocks=ARTIFACT_BLOCKS)
    assert _assert_round_trip(registry, allow_text=allow_text) > MIN_BLOCKS


@pytest.mark.parametrize("allow_text", [True, False])
def test_frontmatter_artifacts_round_trip(allow_text: bool) -> None:
    registry = Registry(syntax=DelimiterFrontmatterSyntax(), blocks={**ARTIFACT_BLOCKS, "note": Note})
    assert _assert_round_trip(registry, allow_text=allow_text) > MIN_BLOCKS


def test_xml_scalar_fields_round_trip() -> None:
    assert _assert_round_trip(Registry(syntax=XmlTagSyntax(tag="block"), blocks={"note": Note})) > MIN_BLOCKS


def test_preamble_round_trip() -> None:
    registry = Registry(syntax=DelimiterPreambleSyntax(), blocks={"note": Note, "command": Command})
    assert _assert_round_trip(registry) > MIN_BLOCKS


def test_preamble_rejects_fields_it_cannot_carry() -> None:
    with pytest.raises(GrammarError, match="cannot carry"):
        Registry(syntax=DelimiterPreambleSyntax(), blocks=ARTIFACT_BLOCKS).to_grammar()


def test_empty_registry_is_rejected() -> None:
    with pytest.raises(GrammarError, match="no block type"):
        Registry().to_grammar()


def test_unknown_dialect_is_rejected() -> None:
    with pytest.raises(GrammarError, match="Unknown grammar dialect"):
        Registry(syntax=XmlTagSyntax(), blocks=ARTIFACT_BLOCKS).to_grammar(dialect="ebnf")


def test_syntax_without_grammar_support() -> None:
    with pytest.raises(NotImplementedError, match="grammar_rules"):
        Registry(syntax=MarkdownFrontmatterSyntax(), blocks={"note": Note}).to_grammar()


def test_to_grammar_output_shape() -> None:
    text = Registry(syntax=XmlTagSyntax(), blocks=ARTIFACT_BLOCKS).to_grammar(dialect=GBNF)
    lines = text.splitlines()
    assert lines[0] == 'root ::= (block "\\n" | text-line)* (block | last-line)?'
    assert "block ::= block-file | block-patch | block-document" in lines
    assert any(line.startswith('block-file ::= "<artifact type=\\"file\\" id=\\"" identifier') for line in lines)
    assert '("create" | "overwrite")' in text
    assert ' "" ' not in text
    assert '("" ' not in text
    names = [line.split(" ::= ")[0] for line in lines]
    assert len(names) == len(set(names))
    assert all(name.replace("-", "").isalnum() for name in names)

    blocks_only = Registry(syntax=XmlTagSyntax(), blocks=ARTIFACT_BLOCKS).to_grammar(allow_text=False)
    assert blocks_only.splitlines()[0] == 'root ::= (block "\\n")* block?'
    assert "text-line" not in blocks_only


def test_field_kinds_from_schema() -> None:
    kinds = {f.name: (f.kind, f.required) for f in block_spec("tagged", Tagged).fields}
    assert kinds == {
        "priority": (FieldKind.INTEGER, False),
        "urgent": (FieldKind.BOOLEAN, False),
        "score": (FieldKind.NUMBER, False),
        "tags": (FieldKind.ANY, False),
    }
    file_fields = {f.name: f for f in block_spec("file", ARTIFACT_BLOCKS["file"]).fields}
    assert file_fields["path"].required
    assert file_fields["path"].non_empty
    assert file_fields["operation"].choices == ("create", "overwrite")


def test_gbnf_rendering_escapes_and_groups() -> None:
    grammar = Grammar(
        rules={
            "root": seq('say "hi"\n', optional(choice("a", "b")), CharSet(chars="]-^\\", ranges=(("a", "z"),))),
            "my_rule": seq(Ref("root"), CharSet(chars="\n", negated=True)),
        }
    )
    assert render_gbnf(grammar).splitlines() == [
        'root ::= "say \\"hi\\"\\n" ("a" | "b")? [\\]\\-\\^\\\\a-z]',
        "my-rule ::= root [^\\n]",
    ]


@pytest.mark.parametrize("non_blank", [False, True])
def test_line_not_starting_with_never_produces_a_marker(non_blank: bool) -> None:
    markers = ("!!end", "!!start", "<<<<<")
    grammar = Grammar(rules={"root": line_not_starting_with(*markers, non_blank=non_blank)})
    rng = Random(SEED)
    lines: list[str] = [sample(grammar, rng) for _ in range(SAMPLES * 10)]
    assert all(line.endswith("\n") and "\n" not in line[:-1] for line in lines)
    assert not any(line.lstrip(" \t").startswith(markers) for line in lines)
    assert any(line.lstrip(" \t").startswith("!!e") for line in lines)
    assert any(not line.strip() for line in lines) is not non_blank


def test_content_class_can_constrain_content() -> None:
    class Answer(BaseContent):
        @classmethod
        def grammar(cls, line: Any) -> Any:
            del line
            return choice("yes\n", "no\n")

    class YesNo(Block[BaseMetadata, Answer]):
        """A yes/no answer."""

    registry = Registry(syntax=XmlTagSyntax(), blocks={"answer": YesNo})
    grammar = build_grammar(registry, allow_text=False)
    rng = Random(SEED)
    contents = {
        event.content["raw_content"]
        for _ in range(SAMPLES)
        for event in _events(registry, sample(grammar, rng))
        if isinstance(event, BlockEndEvent)
    }
    assert contents == {"yes", "no"}


@pytest.mark.parametrize("syntax", [XmlTagSyntax(), DelimiterFrontmatterSyntax()])
def test_prompt_examples_are_accepted_by_the_grammar(syntax: Any) -> None:
    """What the prompt shows a model must be text the grammar lets it write."""
    registry = Registry(syntax=syntax, blocks=ARTIFACT_BLOCKS)
    grammar = build_grammar(registry)
    for block_class in ARTIFACT_BLOCKS.values():
        for example in block_class.get_examples():
            text = f"Here you go:\n{registry.serialize_block(example)}\nDone.\n"
            assert accepts(grammar, text), text
            assert not [e for e in _events(registry, text) if isinstance(e, BlockErrorEvent)]


FRONTMATTER_FILE = "!!start\n---\nid: {id}\nblock_type: file\npath: {path}\n{extra}---\nx = 1\n!!end\n"


@pytest.mark.parametrize(
    ("fields", "accepted"),
    [
        ({"id": "main", "path": "src/main.py"}, True),
        ({"id": '"main"', "path": '"src/main.py"'}, True),
        ({"id": "a", "path": "README"}, True),
        ({"id": "my-file_2", "path": "docs/My notes.md"}, True),
        ({"id": "main", "path": "src/main.py", "extra": "language: python\noperation: overwrite\n"}, True),
        ({"id": "main", "path": "src/main.py", "extra": 'operation: "create"\n'}, True),
        ({"id": "nope", "path": "no way"}, True),
        ({"id": "no", "path": "src/main.py"}, False),
        ({"id": "main", "path": "true"}, False),
        ({"id": "main", "path": "Null"}, False),
        ({"id": "main", "path": "no "}, False),
        ({"id": "main", "path": "123"}, False),
        ({"id": "main", "path": "a: b"}, False),
        ({"id": "main", "path": "src/main.py", "extra": "operation: delete\n"}, False),
        ({"id": "main", "path": "src/main.py", "extra": "operation: overwrite\nlanguage: python\n"}, False),
    ],
)
def test_frontmatter_grammar_accepts_natural_yaml(fields: dict[str, str], accepted: bool) -> None:
    registry = Registry(syntax=DelimiterFrontmatterSyntax(), blocks=ARTIFACT_BLOCKS)
    text = FRONTMATTER_FILE.format(**{"extra": "", **fields})
    assert accepts(build_grammar(registry), text) is accepted
    if accepted:
        events = _events(registry, text)
        assert [type(e).__name__ for e in events if isinstance(e, BlockEndEvent | BlockErrorEvent)] == ["BlockEndEvent"]


def test_accepts_matches_what_the_sampler_produces() -> None:
    registry = Registry(syntax=XmlTagSyntax(), blocks=ARTIFACT_BLOCKS)
    grammar = build_grammar(registry)
    rng = Random(SEED)
    assert all(accepts(grammar, sample(grammar, rng)) for _ in range(50))
    assert accepts(grammar, "")
    assert not accepts(grammar, '<artifact type="file" id="a">\nx\n</artifact>\n')
    assert not accepts(grammar, '<artifact type="file" id="a" path="a.py">\nx\n')


@pytest.mark.parametrize("syntax", [XmlTagSyntax(), DelimiterFrontmatterSyntax()])
@pytest.mark.parametrize("allow_text", [True, False])
def test_min_blocks_requires_blocks(syntax: Any, allow_text: bool) -> None:
    registry = Registry(syntax=syntax, blocks=ARTIFACT_BLOCKS)
    block = registry.serialize_block(FileArtifact.get_examples()[0]) + "\n"
    grammar = build_grammar(registry, allow_text=allow_text, min_blocks=REQUIRED_BLOCKS)

    assert not accepts(grammar, "")
    assert not accepts(grammar, block)
    assert accepts(grammar, block * REQUIRED_BLOCKS)
    assert accepts(grammar, block * (REQUIRED_BLOCKS + 1))
    assert accepts(grammar, f"Sure.\n{block}and\n{block}Done.\n") is allow_text
    assert not accepts(grammar, "Only prose.\n")

    rng = Random(SEED)
    for _ in range(SAMPLES):
        ended = [e for e in _events(registry, sample(grammar, rng)) if isinstance(e, BlockEndEvent)]
        assert len(ended) >= REQUIRED_BLOCKS


def test_min_blocks_must_not_be_negative() -> None:
    registry = Registry(syntax=XmlTagSyntax(), blocks=ARTIFACT_BLOCKS)
    with pytest.raises(GrammarError, match="min_blocks"):
        registry.to_grammar(min_blocks=-1)


@pytest.mark.parametrize("syntax", [XmlTagSyntax(), DelimiterFrontmatterSyntax()])
def test_answer_may_end_without_a_line_break(syntax: Any) -> None:
    """A model that stops right after its last word must not be forced to keep writing."""
    registry = Registry(syntax=syntax, blocks=ARTIFACT_BLOCKS)
    grammar = build_grammar(registry)
    block = registry.serialize_block(FileArtifact.get_examples()[0])

    assert accepts(grammar, "Done.")
    assert accepts(grammar, f"Here you go:\n{block}\nDone.")
    assert accepts(grammar, f"Here you go:\n{block}")
    assert accepts(build_grammar(registry, min_blocks=1), block)
    assert accepts(build_grammar(registry, allow_text=False), f"{block}\n{block}")
    assert not accepts(build_grammar(registry, allow_text=False), f"{block}\nDone.")
