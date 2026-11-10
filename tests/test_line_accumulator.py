"""Tests for LineAccumulator."""

from itertools import pairwise

from hypothesis import given, strategies as st

from hother.streamblocks.core.line_accumulator import LineAccumulator


def _lines(text: str, cuts: list[int], max_line_length: int = 16_384) -> list[tuple[int, str]]:
    acc = LineAccumulator(max_line_length=max_line_length)
    bounds = [0, *sorted(c % (len(text) + 1) for c in cuts), len(text)]
    result = [line for a, b in pairwise(bounds) for line in acc.add_text(text[a:b])]
    final = acc.finalize()
    return [*result, final] if final else result


class TestLineAccumulator:
    def test_complete_lines(self) -> None:
        acc = LineAccumulator()
        assert acc.add_text("") == []
        assert acc.add_text("Line1\n\nLine3\n") == [(1, "Line1"), (2, ""), (3, "Line3")]
        assert acc.finalize() is None

    def test_trailing_newline_does_not_create_empty_line(self) -> None:
        acc = LineAccumulator()
        assert acc.add_text("First\n") == [(1, "First")]
        assert acc.add_text("Second\n") == [(2, "Second")]
        assert acc.line_number == 2

    def test_lines_reassembled_across_chunks(self) -> None:
        acc = LineAccumulator()
        assert acc.add_text("This is a ") == []
        assert acc.has_pending_text
        assert acc.add_text("test\nAnother") == [(1, "This is a test")]
        assert acc.finalize() == (2, "Another")
        assert not acc.has_pending_text
        assert acc.finalize() is None

    def test_crlf_stripped(self) -> None:
        acc = LineAccumulator()
        assert acc.add_text("a\r\nb\r") == [(1, "a")]
        assert acc.add_text("\n") == [(2, "b")]

    def test_truncation(self) -> None:
        acc = LineAccumulator(max_line_length=5)
        assert acc.add_text("Long line\nx") == [(1, "Long ")]
        acc.add_text("y" * 100)
        assert acc.finalize() == (2, "xyyyy")

    def test_buffer_keeps_recent_lines(self) -> None:
        acc = LineAccumulator(buffer_size=2)
        acc.add_text("Line1\nLine2\nLine3\nrest")
        assert acc.buffer == ["Line2", "Line3"]
        acc.finalize()
        assert acc.buffer == ["Line3", "rest"]

    def test_reset(self) -> None:
        acc = LineAccumulator()
        acc.add_text("Old\npending")
        acc.reset()
        assert (acc.line_number, acc.buffer, acc.has_pending_text) == (0, [], False)
        assert acc.add_text("New\n") == [(1, "New")]

    @given(st.text(alphabet="ab\r\n", max_size=60), st.lists(st.integers(min_value=0), max_size=8))
    def test_chunking_does_not_change_lines(self, text: str, cuts: list[int]) -> None:
        assert _lines(text, cuts, max_line_length=4) == _lines(text, [], max_line_length=4)
