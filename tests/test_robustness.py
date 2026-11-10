"""Robustness tests for malformed or adversarial streams."""

from itertools import pairwise
from typing import Any

from hypothesis import given, settings, strategies as st

from hother.streamblocks import DelimiterFrontmatterSyntax, DelimiterPreambleSyntax, Registry, StreamBlockProcessor
from hother.streamblocks.core.processor import ProcessorConfig
from hother.streamblocks.core.types import BlockEndEvent, BlockErrorCode, BlockErrorEvent, Event, TextContentEvent


def _run(text: str, cuts: tuple[int, ...] = (), registry: Registry | None = None, **config: Any) -> list[Event]:
    processor = StreamBlockProcessor(
        registry or Registry(syntax=DelimiterPreambleSyntax()),
        ProcessorConfig(emit_text_deltas=False, **config),
    )
    bounds = [0, *sorted(c % (len(text) + 1) for c in cuts), len(text)]
    events = [e for a, b in pairwise(bounds) for e in processor.process_chunk(text[a:b])]
    return [*events, *processor.finalize()]


def _outcomes(events: list[Event]) -> list[tuple[str, str]]:
    return [
        (type(e).__name__, e.raw_content if isinstance(e, BlockEndEvent) else e.reason)
        for e in events
        if isinstance(e, BlockEndEvent | BlockErrorEvent)
    ]


def test_crlf_stream() -> None:
    assert _outcomes(_run("!!a1:note\r\nhello\r\n!!end\r\n")) == [("BlockEndEvent", "!!a1:note\nhello\n!!end")]


def test_markers_tolerate_trailing_whitespace() -> None:
    assert _outcomes(_run("!!a1:note  \nhello\n!!end \n")) == [("BlockEndEvent", "!!a1:note  \nhello\n!!end ")]


def test_unclosed_block_is_interrupted_by_next_opening() -> None:
    events = _run("!!a1:note\nlost\n!!b2:note\nkept\n!!end\n")
    errors = [e for e in events if isinstance(e, BlockErrorEvent)]
    assert [e.error_code for e in errors] == [BlockErrorCode.UNCLOSED_BLOCK]
    assert [e.raw_content for e in events if isinstance(e, BlockEndEvent)] == ["!!b2:note\nkept\n!!end"]


def test_size_limit_includes_closing_line() -> None:
    errors = [e for e in _run("!!a1:note\nab\n!!end\n", max_block_size=14) if isinstance(e, BlockErrorEvent)]
    assert [e.error_code for e in errors] == [BlockErrorCode.SIZE_EXCEEDED]


def test_raising_validator_becomes_block_error() -> None:
    registry = Registry(syntax=DelimiterPreambleSyntax())

    def boom(_block: Any) -> bool:
        raise RuntimeError("boom")

    registry.add_validator("note", boom)
    events = _run("!!a1:note\nx\n!!end\n!!b2:other\ny\n!!end\n", registry=registry)
    assert [name for name, _ in _outcomes(events)] == ["BlockErrorEvent", "BlockEndEvent"]


@settings(max_examples=200)
@given(
    st.lists(st.sampled_from(["!!a1:note", "!!end", "text", "", "!!b2:x:y"]), max_size=12),
    st.lists(st.integers(min_value=0), max_size=6),
)
def test_chunking_does_not_change_blocks(lines: list[str], cuts: list[int]) -> None:
    text = "\n".join(lines)
    assert _outcomes(_run(text, tuple(cuts))) == _outcomes(_run(text))


def test_event_ids_are_unique_uuids() -> None:
    from uuid import UUID

    from hother.streamblocks.core.types import TextContentEvent

    ids = {TextContentEvent(content="", line_number=1).event_id for _ in range(100)}
    assert len(ids) == 100
    assert all(UUID(i) for i in ids)


def test_text_after_closing_marker_is_reprocessed() -> None:
    events = _run("!!a1:note\nhello\n!!endYour answer\n")
    assert _outcomes(events) == [("BlockEndEvent", "!!a1:note\nhello\n!!end")]
    assert [e.content for e in events if isinstance(e, TextContentEvent)] == ["Your answer"]


def test_text_after_closing_marker_frontmatter() -> None:
    registry = Registry(syntax=DelimiterFrontmatterSyntax())
    events = _run("!!start\n---\nid: a1\nblock_type: note\n---\nhello\n!!end  Your answer\n", registry=registry)
    assert [e.raw_content.splitlines()[-1] for e in events if isinstance(e, BlockEndEvent)] == ["!!end"]
    assert [e.content for e in events if isinstance(e, TextContentEvent)] == ["Your answer"]


def test_opening_marker_after_closing_marker_starts_a_block() -> None:
    events = _run("!!a1:note\nhello\n!!end!!b2:note\nkept\n!!end\n")
    assert [raw for _, raw in _outcomes(events)] == ["!!a1:note\nhello\n!!end", "!!b2:note\nkept\n!!end"]


def test_opening_marker_starting_with_end_is_not_a_close() -> None:
    events = _run("!!a1:note\nlost\n!!endpoint:note\nkept\n!!end\n")
    assert [e.error_code for e in events if isinstance(e, BlockErrorEvent)] == [BlockErrorCode.UNCLOSED_BLOCK]
    assert [e.raw_content for e in events if isinstance(e, BlockEndEvent)] == ["!!endpoint:note\nkept\n!!end"]


def test_lenient_close_can_be_disabled() -> None:
    registry = Registry(syntax=DelimiterPreambleSyntax(lenient_close=False))
    events = _run("!!a1:note\nhello\n!!endYour answer\n", registry=registry)
    assert [e.error_code for e in events if isinstance(e, BlockErrorEvent)] == [BlockErrorCode.UNCLOSED_BLOCK]
