"""Tests for stream validators and stream abort."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from hother.streamblocks import (
    DelimiterFrontmatterSyntax,
    PartialBlock,
    Registry,
    StreamBlockProcessor,
    ValidationResult,
    XmlTagSyntax,
)
from hother.streamblocks.blocks.artifacts import ARTIFACT_BLOCKS
from hother.streamblocks.core.processor import ProcessorConfig
from hother.streamblocks.core.types import (
    BlockContentDeltaEvent,
    BlockEndEvent,
    BlockErrorCode,
    BlockErrorEvent,
    Event,
    SectionType,
    TextContentEvent,
)
from hother.streamblocks.guards import forbid_patterns, max_lines, max_size, path_within

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

GOOD = '<artifact type="file" id="ok" path="src/ok.py">\nx = 1\n</artifact>\n'
BAD = '<artifact type="file" id="bad" path="../secrets.env">\nTOKEN = 1\nMORE = 2\n</artifact>\n'


def _registry() -> Registry:
    return Registry(syntax=XmlTagSyntax(), blocks=ARTIFACT_BLOCKS)


def _run(registry: Registry, text: str, *, abort: bool = False) -> tuple[list[Event], StreamBlockProcessor]:
    processor = StreamBlockProcessor(registry, ProcessorConfig(emit_text_deltas=False, abort_stream_on_failure=abort))
    events = [e for line in text.splitlines(keepends=True) for e in processor.process_chunk(line)]
    return [*events, *processor.finalize()], processor


def _errors(events: list[Event]) -> list[BlockErrorEvent]:
    return [e for e in events if isinstance(e, BlockErrorEvent)]


def _ended(events: list[Event]) -> list[str]:
    return [str(e.metadata["id"]) for e in events if isinstance(e, BlockEndEvent)]


def test_block_is_rejected_on_its_opening_line() -> None:
    registry = _registry()
    registry.add_stream_validator(path_within("src"))
    events, processor = _run(registry, BAD + GOOD)

    (error,) = _errors(events)
    assert error.error_code == BlockErrorCode.ABORTED
    assert "outside the project" in error.reason
    assert error.end_line == 1
    assert not [e for e in events if isinstance(e, BlockContentDeltaEvent) and "TOKEN" in e.delta]
    # Without stream abort, the rest of the rejected block is plain text and later blocks still extract
    assert "TOKEN = 1" in [e.content for e in events if isinstance(e, TextContentEvent)]
    assert _ended(events) == ["ok"]
    assert not processor.aborted


def test_stream_abort_stops_processing() -> None:
    registry = _registry()
    registry.add_stream_validator(path_within("src"))
    events, processor = _run(registry, GOOD + BAD + GOOD, abort=True)

    assert _ended(events) == ["ok"]
    assert [e.error_code for e in _errors(events)] == [BlockErrorCode.ABORTED]
    assert isinstance(events[-1], BlockErrorEvent)
    assert processor.aborted
    assert processor.process_chunk(GOOD) == []
    assert processor.finalize() == []


@pytest.mark.asyncio
async def test_process_stream_closes_the_producer_on_abort() -> None:
    registry = _registry()
    registry.add_stream_validator(forbid_patterns(r"\bTOKEN\b"))
    produced: list[str] = []
    closed = False

    async def producer() -> AsyncIterator[str]:
        nonlocal closed
        try:
            for line in (BAD + GOOD).splitlines(keepends=True):
                produced.append(line)
                yield line
        finally:
            closed = True

    processor = StreamBlockProcessor(registry, ProcessorConfig(abort_stream_on_failure=True))
    events = [event async for event in processor.process_stream(producer())]

    assert [e.error_code for e in events if isinstance(e, BlockErrorEvent)] == [BlockErrorCode.ABORTED]
    assert produced == BAD.splitlines(keepends=True)[:2]
    assert closed
    assert processor.aborted


def test_typed_validator_only_sees_its_block_type() -> None:
    registry = _registry()
    seen: list[PartialBlock] = []

    def record(partial: PartialBlock) -> ValidationResult:
        seen.append(partial)
        return ValidationResult.success()

    registry.add_stream_validator(record, "patch")
    _run(registry, GOOD)
    assert not seen

    patch = '<artifact type="patch" id="p" path="a.py">\n<<<<<<< SEARCH\na\n=======\nb\n>>>>>>> REPLACE\n</artifact>\n'
    events, _ = _run(registry, patch)
    assert _ended(events) == ["p"]
    assert [p.line for p in seen] == patch.splitlines()[:-1]
    assert {p.block_type for p in seen} == {"patch"}
    assert seen[0].section == SectionType.HEADER
    assert seen[-1].section == SectionType.CONTENT
    assert seen[-1].metadata == {"id": "p", "path": "a.py", "block_type": "patch"}
    assert list(seen[-1].content_lines) == patch.splitlines()[1:-1]


def test_frontmatter_metadata_is_known_once_the_section_ends() -> None:
    registry = Registry(syntax=DelimiterFrontmatterSyntax(), blocks=ARTIFACT_BLOCKS)
    registry.add_stream_validator(path_within("src"))
    text = "!!start\n---\nid: bad\nblock_type: file\npath: /etc/passwd\n---\nroot:x:0:0\nmore\n!!end\n"
    events, _ = _run(registry, text)

    (error,) = _errors(events)
    assert error.error_code == BlockErrorCode.ABORTED
    assert error.end_line == 6
    assert not [e for e in events if isinstance(e, BlockContentDeltaEvent)]


def test_content_guards() -> None:
    for validator, reason, line in [
        (max_lines(1), "exceeds 1 lines", 3),
        (max_size(60), "exceeds 60 characters", 2),
        (forbid_patterns("MORE"), "forbidden pattern 'MORE'", 3),
    ]:
        registry = _registry()
        registry.add_stream_validator(validator)
        (error,) = _errors(_run(registry, BAD)[0])
        assert error.error_code == BlockErrorCode.ABORTED
        assert reason in error.reason
        assert error.end_line == line
        assert _ended(_run(registry, GOOD)[0]) == ["ok"]


@pytest.mark.parametrize(
    ("path", "roots", "allowed"),
    [
        ("src/a.py", ("src",), True),
        ("src/pkg/../a.py", ("src",), True),
        ("src", ("src",), True),
        ("srcs/a.py", ("src",), False),
        ("tests/a.py", ("src", "tests/"), True),
        ("docs/a.md", ("src", "tests"), False),
        ("src/../../a.py", ("src",), False),
        ("/abs/a.py", (), False),
        ("C:\\Windows\\a.py", (), False),
        ("..\\a.py", (), False),
        ("anything/a.py", (), True),
    ],
)
def test_path_within(path: str, roots: tuple[str, ...], allowed: bool) -> None:
    partial = PartialBlock(
        block_type="file",
        metadata={"path": path},
        section=SectionType.HEADER,
        line="",
        line_number=1,
        lines=(),
        content_lines=(),
        size=0,
    )
    assert path_within(*roots)(partial).passed is allowed


def test_path_guard_ignores_blocks_without_the_field() -> None:
    registry = _registry()
    registry.add_stream_validator(path_within("src"))
    events, _ = _run(registry, '<artifact type="document" id="d" title="Notes">\nhello\n</artifact>\n')
    assert _ended(events) == ["d"]


def test_raising_validator_becomes_a_block_error() -> None:
    registry = _registry()

    def boom(_partial: PartialBlock) -> ValidationResult:
        raise RuntimeError("boom")

    registry.add_stream_validator(boom)
    events, processor = _run(registry, GOOD + GOOD, abort=True)
    assert [e.error_code for e in _errors(events)] == [BlockErrorCode.PARSE_FAILED, BlockErrorCode.PARSE_FAILED]
    assert not processor.aborted


def test_no_stream_validators_changes_nothing() -> None:
    events, _ = _run(_registry(), GOOD + BAD)
    assert _ended(events) == ["ok", "bad"]
    assert not _errors(events)
