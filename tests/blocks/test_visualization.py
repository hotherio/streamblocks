"""Tests for visualization block models."""

from __future__ import annotations

import pytest

from hother.streamblocks_examples.blocks.agent.visualization import (
    VisualizationContent,
    VisualizationMetadata,
)


class TestVisualizationMetadata:
    """Tests for VisualizationMetadata model."""

    def test_create_metadata(self) -> None:
        """Test creating visualization metadata."""
        metadata = VisualizationMetadata(
            block_type="visualization",
            id="viz-1",
            viz_type="chart",
            title="Test Chart",
        )
        assert metadata.viz_type == "chart"
        assert metadata.title == "Test Chart"
        assert metadata.format == "markdown"  # default

    def test_all_viz_types(self) -> None:
        """Test all valid visualization types."""
        for viz_type in ["chart", "diagram", "table", "code", "ascii_art"]:
            metadata = VisualizationMetadata(
                block_type="visualization",
                id="test",
                viz_type=viz_type,  # type: ignore[arg-type]
                title="Test",
            )
            assert metadata.viz_type == viz_type

    def test_all_format_types(self) -> None:
        """Test all valid format types."""
        for fmt in ["ascii", "markdown", "html"]:
            metadata = VisualizationMetadata(
                block_type="visualization",
                id="test",
                viz_type="chart",
                title="Test",
                format=fmt,  # type: ignore[arg-type]
            )
            assert metadata.format == fmt

    def test_optional_dimensions(self) -> None:
        """Test optional width and height."""
        metadata = VisualizationMetadata(
            block_type="visualization",
            id="test",
            viz_type="diagram",
            title="Diagram",
            width=800,
            height=600,
        )
        assert metadata.width == 800
        assert metadata.height == 600


class TestVisualizationContentParse:
    """Tests for VisualizationContent.parse()."""

    def test_parse_valid_yaml(self) -> None:
        """Test parsing valid YAML data."""
        raw = "labels:\n  - A\n  - B\nvalues:\n  - 10\n  - 20"
        content = VisualizationContent.parse(raw)
        assert content.data["labels"] == ["A", "B"]
        assert content.data["values"] == [10, 20]
        assert content.raw_content == raw

    def test_parse_nested_data(self) -> None:
        """Test parsing nested YAML structure."""
        raw = "chart:\n  type: bar\n  series:\n    - name: Sales\n      values: [1, 2, 3]"
        content = VisualizationContent.parse(raw)
        assert content.data["chart"]["type"] == "bar"
        assert content.data["chart"]["series"][0]["values"] == [1, 2, 3]

    def test_parse_empty_yaml(self) -> None:
        """Test parsing empty YAML returns empty dict."""
        content = VisualizationContent.parse("")
        assert content.data == {}

    def test_parse_null_yaml(self) -> None:
        """Test parsing null YAML returns empty dict."""
        content = VisualizationContent.parse("null")
        assert content.data == {}

    def test_parse_invalid_yaml_raises_error(self) -> None:
        """Test that invalid YAML raises ValueError.

        This covers lines 32-38.
        """
        with pytest.raises(ValueError, match="Invalid YAML data"):
            VisualizationContent.parse("[unclosed: bracket")

    def test_parse_invalid_yaml_multiline(self) -> None:
        """Test invalid YAML across multiple lines."""
        raw = "data: [value\nmissing: close"
        with pytest.raises(ValueError, match="Invalid YAML"):
            VisualizationContent.parse(raw)

    def test_rendered_is_none_by_default(self) -> None:
        """Test that rendered field is None by default."""
        content = VisualizationContent.parse("key: value")
        assert content.rendered is None

    def test_parse_complex_structure(self) -> None:
        """Test parsing complex visualization data."""
        raw = """
type: scatter
x: [1, 2, 3, 4, 5]
y: [2, 4, 1, 5, 3]
options:
  marker: circle
  color: blue
  size: 10
"""
        content = VisualizationContent.parse(raw)
        assert content.data["type"] == "scatter"
        assert content.data["x"] == [1, 2, 3, 4, 5]
        assert content.data["options"]["marker"] == "circle"
