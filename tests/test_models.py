"""Tests for core models."""

from hother.streamblocks import DelimiterPreambleSyntax
from hother.streamblocks.core.models import BlockCandidate, extract_block_types
from hother.streamblocks.core.types import BaseContent, BaseMetadata, BlockState


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
        assert "section=" in repr_str
        assert "HEADER" in repr_str

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


class TestExtractBlockTypes:
    """Tests for extract_block_types function."""

    def test_extract_block_types_no_model_fields(self) -> None:
        """Test extract_block_types with class having no model_fields.

        This covers line 38 of models.py (fallback case).
        """

        # A plain class without model_fields attribute
        class PlainClass:
            pass

        metadata, content = extract_block_types(PlainClass)

        assert metadata is BaseMetadata
        assert content is BaseContent

    def test_extract_block_types_missing_metadata_field(self) -> None:
        """Test extract_block_types with class missing metadata field.

        This also covers line 38 of models.py (fallback case).
        """

        class PartialModel:
            # Has model_fields but missing metadata field
            model_fields = {"content": object()}

        metadata, content = extract_block_types(PartialModel)

        assert metadata is BaseMetadata
        assert content is BaseContent

    def test_extract_block_types_missing_content_field(self) -> None:
        """Test extract_block_types with class missing content field.

        This also covers line 38 of models.py (fallback case).
        """

        class PartialModel:
            # Has model_fields but missing content field
            model_fields = {"metadata": object()}

        metadata, content = extract_block_types(PartialModel)

        assert metadata is BaseMetadata
        assert content is BaseContent

    def test_extract_block_types_with_none_annotations(self) -> None:
        """Test extract_block_types with BaseModel having None annotations.

        This covers the fallback branch (34->43) when a BaseModel subclass exists
        but field annotations are None.
        """
        from unittest.mock import MagicMock

        from pydantic import BaseModel

        # Create a mock BaseModel subclass
        class MockBlock(BaseModel):
            pass

        # Mock model_fields to have fields with None annotations
        mock_metadata_field = MagicMock()
        mock_metadata_field.annotation = None
        mock_content_field = MagicMock()
        mock_content_field.annotation = None

        MockBlock.model_fields = {
            "metadata": mock_metadata_field,
            "content": mock_content_field,
        }

        metadata, content = extract_block_types(MockBlock)

        assert metadata is BaseMetadata
        assert content is BaseContent
