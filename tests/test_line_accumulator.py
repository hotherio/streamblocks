"""Tests for LineAccumulator."""

from hother.streamblocks.core.line_accumulator import LineAccumulator


class TestLineAccumulatorBasics:
    """Basic functionality tests for LineAccumulator."""

    def test_empty_text_returns_empty(self) -> None:
        """Empty text should return empty list."""
        acc = LineAccumulator()
        result = acc.add_text("")
        assert result == []

    def test_single_complete_line(self) -> None:
        """Single complete line should be returned with trailing empty."""
        acc = LineAccumulator()
        result = acc.add_text("Hello\n")
        # "Hello\n".split("\n") = ["Hello", ""] - trailing empty is included
        assert len(result) == 2
        assert result[0] == (1, "Hello")
        assert result[1] == (2, "")

    def test_multiple_complete_lines(self) -> None:
        """Multiple complete lines should all be returned with trailing empty."""
        acc = LineAccumulator()
        result = acc.add_text("Line1\nLine2\nLine3\n")
        # Trailing newline creates empty line at end
        assert len(result) == 4
        assert result[0] == (1, "Line1")
        assert result[1] == (2, "Line2")
        assert result[2] == (3, "Line3")
        assert result[3] == (4, "")

    def test_incomplete_line_buffered(self) -> None:
        """Incomplete line should be buffered."""
        acc = LineAccumulator()
        result = acc.add_text("Hello")
        assert result == []
        assert acc.has_pending_text

    def test_incomplete_line_completed_on_next_call(self) -> None:
        """Incomplete line should be completed on next call."""
        acc = LineAccumulator()
        result1 = acc.add_text("Hel")
        assert result1 == []

        result2 = acc.add_text("lo\n")
        # Trailing newline creates empty line at end
        assert len(result2) == 2
        assert result2[0] == (1, "Hello")
        assert result2[1] == (2, "")


class TestLineAccumulatorChunking:
    """Tests for chunked text processing."""

    def test_split_across_chunks(self) -> None:
        """Lines split across chunks should be reassembled."""
        acc = LineAccumulator()

        # First chunk: partial line
        result1 = acc.add_text("This is a ")
        assert result1 == []

        # Second chunk: rest of line + complete line
        result2 = acc.add_text("test\nAnother line\n")
        # Trailing newline creates empty line at end
        assert len(result2) == 3
        assert result2[0] == (1, "This is a test")
        assert result2[1] == (2, "Another line")
        assert result2[2] == (3, "")

    def test_newline_in_middle_of_chunk(self) -> None:
        """Newlines in middle of chunks should create lines."""
        acc = LineAccumulator()
        result = acc.add_text("First\nSecond")
        assert len(result) == 1
        assert result[0] == (1, "First")
        assert acc.has_pending_text

    def test_multiple_chunks_one_line(self) -> None:
        """Many chunks forming one line should work."""
        acc = LineAccumulator()

        acc.add_text("a")
        acc.add_text("b")
        acc.add_text("c")
        result = acc.add_text("d\n")

        # Trailing newline creates empty line at end
        assert len(result) == 2
        assert result[0] == (1, "abcd")
        assert result[1] == (2, "")


class TestLineAccumulatorFinalize:
    """Tests for finalize behavior."""

    def test_finalize_with_pending_text(self) -> None:
        """Finalize should return pending text as final line."""
        acc = LineAccumulator()
        acc.add_text("incomplete")

        result = acc.finalize()
        assert result is not None
        assert result == (1, "incomplete")
        assert not acc.has_pending_text

    def test_finalize_without_pending_text(self) -> None:
        """Finalize without pending text should return None."""
        acc = LineAccumulator()
        acc.add_text("complete\n")

        result = acc.finalize()
        assert result is None

    def test_finalize_clears_accumulated_text(self) -> None:
        """Finalize should clear accumulated text."""
        acc = LineAccumulator()
        acc.add_text("pending")

        acc.finalize()
        assert not acc.has_pending_text

        # Second finalize should return None
        result = acc.finalize()
        assert result is None


class TestLineAccumulatorTruncation:
    """Tests for line length truncation."""

    def test_long_line_truncated(self) -> None:
        """Lines exceeding max length should be truncated."""
        acc = LineAccumulator(max_line_length=10)
        result = acc.add_text("This is a very long line\n")

        # Trailing newline creates empty line at end
        assert len(result) == 2
        assert result[0][1] == "This is a "
        assert len(result[0][1]) == 10

    def test_short_line_not_truncated(self) -> None:
        """Lines within max length should not be truncated."""
        acc = LineAccumulator(max_line_length=100)
        result = acc.add_text("Short\n")

        assert result[0][1] == "Short"

    def test_truncation_on_finalize(self) -> None:
        """Truncation should apply on finalize too."""
        acc = LineAccumulator(max_line_length=5)
        acc.add_text("Long text without newline")

        result = acc.finalize()
        assert result is not None
        assert result[1] == "Long "
        assert len(result[1]) == 5


class TestLineAccumulatorBuffer:
    """Tests for recent lines buffer."""

    def test_buffer_contains_recent_lines(self) -> None:
        """Buffer should contain recent lines."""
        acc = LineAccumulator(buffer_size=4)
        acc.add_text("Line1\nLine2\nLine3\n")

        buffer = acc.buffer
        # Includes trailing empty line
        assert len(buffer) == 4
        assert buffer == ["Line1", "Line2", "Line3", ""]

    def test_buffer_limited_to_size(self) -> None:
        """Buffer should only keep buffer_size lines."""
        acc = LineAccumulator(buffer_size=2)
        acc.add_text("Line1\nLine2\nLine3\nLine4\n")

        buffer = acc.buffer
        # Last 2 are "Line4" and trailing empty
        assert len(buffer) == 2
        assert buffer == ["Line4", ""]

    def test_buffer_includes_finalized_line(self) -> None:
        """Buffer should include finalized line."""
        acc = LineAccumulator(buffer_size=5)
        acc.add_text("Line1\n")
        acc.add_text("incomplete")
        acc.finalize()

        buffer = acc.buffer
        # Line1, trailing empty from \n, then finalized incomplete
        assert len(buffer) == 3
        assert buffer == ["Line1", "", "incomplete"]


class TestLineAccumulatorLineNumbers:
    """Tests for line number tracking."""

    def test_line_numbers_increment(self) -> None:
        """Line numbers should increment correctly."""
        acc = LineAccumulator()
        assert acc.line_number == 0

        acc.add_text("First\n")
        # "First" is line 1, trailing empty is line 2
        assert acc.line_number == 2

        acc.add_text("Second\n")
        # "Second" is line 3, trailing empty is line 4
        assert acc.line_number == 4

    def test_line_number_after_finalize(self) -> None:
        """Line number should increment on finalize."""
        acc = LineAccumulator()
        acc.add_text("Line1\n")
        acc.add_text("incomplete")

        acc.finalize()
        # Line1=1, trailing empty=2, finalized incomplete=3
        assert acc.line_number == 3


class TestLineAccumulatorReset:
    """Tests for reset functionality."""

    def test_reset_clears_all_state(self) -> None:
        """Reset should clear all state."""
        acc = LineAccumulator(buffer_size=5)
        acc.add_text("Line1\nLine2\n")
        acc.add_text("pending")

        acc.reset()

        assert acc.line_number == 0
        assert acc.buffer == []
        assert not acc.has_pending_text

    def test_can_use_after_reset(self) -> None:
        """Accumulator should work normally after reset."""
        acc = LineAccumulator()
        acc.add_text("Old\n")
        acc.reset()

        result = acc.add_text("New\n")
        # Trailing newline creates empty line at end
        assert len(result) == 2
        assert result[0] == (1, "New")
        assert result[1] == (2, "")


class TestLineAccumulatorEmptyLines:
    """Tests for empty line handling."""

    def test_empty_lines_preserved(self) -> None:
        """Empty lines should be preserved."""
        acc = LineAccumulator()
        result = acc.add_text("Line1\n\nLine3\n")

        # Includes trailing empty from final \n
        assert len(result) == 4
        assert result[0][1] == "Line1"
        assert result[1][1] == ""
        assert result[2][1] == "Line3"
        assert result[3][1] == ""

    def test_multiple_consecutive_newlines(self) -> None:
        """Multiple consecutive newlines should create empty lines."""
        acc = LineAccumulator()
        result = acc.add_text("\n\n\n")

        # "\n\n\n".split("\n") = ["", "", "", ""] - 4 empty strings
        assert len(result) == 4
        assert all(line == "" for _, line in result)
