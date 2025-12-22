"""Tests for core models."""

from hother.streamblocks import DelimiterPreambleSyntax
from hother.streamblocks.core.models import BlockCandidate
from hother.streamblocks.core.types import BlockState


class TestBlockCandidate:
    """Tests for BlockCandidate model."""

    def test_repr_initial_state(self) -> None:
        """Test __repr__ on freshly created candidate."""
        syntax = DelimiterPreambleSyntax()
        candidate = BlockCandidate(syntax, start_line=1)

        repr_str = repr(candidate)

        assert "BlockCandidate(" in repr_str
        assert "syntax=DelimiterPreambleSyntax" in repr_str
        assert "start_line=1" in repr_str
        assert "state=header_detected" in repr_str
        assert "lines=0" in repr_str
        assert "section='header'" in repr_str

    def test_repr_with_lines(self) -> None:
        """Test __repr__ after adding lines."""
        syntax = DelimiterPreambleSyntax()
        candidate = BlockCandidate(syntax, start_line=5)
        candidate.add_line("line 1")
        candidate.add_line("line 2")
        candidate.add_line("line 3")

        repr_str = repr(candidate)

        assert "start_line=5" in repr_str
        assert "lines=3" in repr_str

    def test_repr_with_different_state(self) -> None:
        """Test __repr__ with different block states."""
        syntax = DelimiterPreambleSyntax()
        candidate = BlockCandidate(syntax, start_line=1)
        candidate.state = BlockState.ACCUMULATING_CONTENT

        repr_str = repr(candidate)

        assert "state=accumulating_content" in repr_str

    def test_repr_with_different_section(self) -> None:
        """Test __repr__ with different current section."""
        syntax = DelimiterPreambleSyntax()
        candidate = BlockCandidate(syntax, start_line=1)
        candidate.current_section = "metadata"

        repr_str = repr(candidate)

        assert "section='metadata'" in repr_str

    def test_repr_is_valid_string(self) -> None:
        """Test that __repr__ returns a valid string for debugging."""
        syntax = DelimiterPreambleSyntax()
        candidate = BlockCandidate(syntax, start_line=10)
        candidate.add_line("test content")
        candidate.current_section = "content"
        candidate.state = BlockState.ACCUMULATING_CONTENT

        repr_str = repr(candidate)

        # Should be a non-empty string
        assert isinstance(repr_str, str)
        assert len(repr_str) > 0

        # Should contain all key information
        assert "DelimiterPreambleSyntax" in repr_str
        assert "10" in repr_str
        assert "1" in repr_str  # lines=1
        assert "content" in repr_str
