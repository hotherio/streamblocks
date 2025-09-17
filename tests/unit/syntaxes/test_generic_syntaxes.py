"""Tests for generic built-in syntax implementations."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from streamblocks.core.models import BlockCandidate
from streamblocks.core.types import BlockState
from streamblocks.syntaxes.builtin import (
    DelimiterFrontmatterSyntax,
    DelimiterPreambleSyntax,
    MarkdownFrontmatterSyntax,
)


# Test Models for DelimiterPreambleSyntax
class TestPreambleMetadata(BaseModel):
    """Test metadata model for delimiter preamble blocks."""

    id: str = Field(description="Block identifier")
    type: str = Field(default="block", description="Block type")
    params: str | None = Field(None, description="Optional parameters")


class TestPreambleContent(BaseModel):
    """Test content model for delimiter preamble blocks."""

    text: str = Field(description="Block content")
    line_count: int = Field(default=0, description="Number of lines")

    def __init__(self, **data: Any) -> None:
        """Initialize with computed fields."""
        super().__init__(**data)
        if "line_count" not in data and "text" in data:
            self.line_count = len(data["text"].splitlines())


# Test Models for MarkdownFrontmatterSyntax
class TestMarkdownMetadata(BaseModel):
    """Test metadata model for markdown frontmatter blocks."""

    id: str | None = Field(None, description="Block ID")
    type: str | None = Field(None, description="Block type")
    title: str | None = Field(None, description="Block title")
    tags: list[str] = Field(default_factory=list, description="Tags")


class TestMarkdownContent(BaseModel):
    """Test content model for markdown blocks."""

    text: str = Field(description="Content text")
    format: str = Field(default="markdown", description="Content format")


# Test Models for DelimiterFrontmatterSyntax
class TestDelimiterMetadata(BaseModel):
    """Test metadata model for delimiter frontmatter blocks."""

    id: str = Field(description="Block ID")
    name: str = Field(description="Block name")
    path: str | None = Field(None, description="File path")


class TestDelimiterContent(BaseModel):
    """Test content model for delimiter frontmatter blocks."""

    raw: str = Field(description="Raw content")

    @classmethod
    def parse(cls, text: str) -> TestDelimiterContent:
        """Parse text into content model."""
        return cls(raw=text)


class TestDelimiterPreambleSyntax:
    """Tests for delimiter preamble syntax parser."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.syntax = DelimiterPreambleSyntax(
            metadata_class=TestPreambleMetadata,
            content_class=TestPreambleContent,
        )

    def test_detect_opening_delimiter(self) -> None:
        """Test detection of opening delimiter with inline metadata."""
        result = self.syntax.detect_line("!!block123:shell:bash", None)
        assert result.is_opening
        assert result.metadata
        assert result.metadata["_raw_preamble"] == "block123:shell:bash"

    def test_detect_closing_delimiter(self) -> None:
        """Test detection of closing delimiter."""
        candidate = BlockCandidate(syntax=self.syntax, start_line=1)
        candidate.state = BlockState.ACCUMULATING_CONTENT

        result = self.syntax.detect_line("!!end", candidate)
        assert result.is_closing

    def test_parse_simple_block(self) -> None:
        """Test parsing a simple delimiter block."""
        candidate = BlockCandidate(syntax=self.syntax, start_line=1)
        candidate.state = BlockState.COMPLETED
        candidate.lines = [
            "!!abc123:python",
            "print('Hello')",
            "print('World')",
            "!!end",
        ]
        candidate.content_lines = ["print('Hello')", "print('World')"]
        candidate.metadata = {"_raw_preamble": "abc123:python"}

        result = self.syntax.parse_block(candidate)
        assert result.success
        assert result.metadata
        assert result.metadata.id == "abc123"
        assert result.metadata.type == "python"
        assert result.content
        assert result.content.text == "print('Hello')\nprint('World')"
        assert result.content.line_count == 2

    def test_parse_with_params(self) -> None:
        """Test parsing block with additional parameters."""
        candidate = BlockCandidate(syntax=self.syntax, start_line=1)
        candidate.state = BlockState.COMPLETED
        candidate.lines = [
            "!!file01:operation:create",
            "src/main.py:C",
            "README.md:E",
            "!!end",
        ]
        candidate.content_lines = ["src/main.py:C", "README.md:E"]
        candidate.metadata = {"_raw_preamble": "file01:operation:create"}

        result = self.syntax.parse_block(candidate)
        assert result.success
        assert result.metadata
        assert result.metadata.id == "file01"
        assert result.metadata.type == "operation"
        assert result.metadata.params == "create"


class TestMarkdownFrontmatterSyntax:
    """Tests for markdown frontmatter syntax parser."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.syntax = MarkdownFrontmatterSyntax(
            metadata_class=TestMarkdownMetadata,
            content_class=TestMarkdownContent,
        )

    def test_detect_opening_fence(self) -> None:
        """Test detection of opening fence."""
        result = self.syntax.detect_line("```", None)
        assert result.is_opening
        assert not result.is_closing

    def test_detect_frontmatter_boundaries(self) -> None:
        """Test detection of frontmatter boundaries."""
        candidate = BlockCandidate(syntax=self.syntax, start_line=1)
        candidate.state = BlockState.HEADER_DETECTED

        # First --- should be metadata boundary
        result = self.syntax.detect_line("---", candidate)
        assert result.is_metadata_boundary

    def test_parse_with_frontmatter(self) -> None:
        """Test parsing markdown block with frontmatter."""
        candidate = BlockCandidate(syntax=self.syntax, start_line=1)
        candidate.state = BlockState.COMPLETED
        candidate.lines = [
            "```",
            "---",
            "id: test-block",
            "type: documentation",
            "tags: [python, example]",
            "---",
            "# Example Code",
            "This is content",
            "```",
        ]
        candidate.metadata_lines = [
            "id: test-block",
            "type: documentation",
            "tags: [python, example]",
        ]
        candidate.content_lines = ["# Example Code", "This is content"]

        result = self.syntax.parse_block(candidate)
        assert result.success
        assert result.metadata
        assert result.metadata.id == "test-block"
        assert result.metadata.type == "documentation"
        assert result.metadata.tags == ["python", "example"]
        assert result.content
        assert result.content.text == "# Example Code\nThis is content"
        assert result.content.format == "markdown"

    def test_parse_without_frontmatter(self) -> None:
        """Test parsing markdown block without frontmatter."""
        candidate = BlockCandidate(syntax=self.syntax, start_line=1)
        candidate.state = BlockState.COMPLETED
        candidate.lines = [
            "```",
            "Just content",
            "No metadata",
            "```",
        ]
        candidate.metadata_lines = []
        candidate.content_lines = ["Just content", "No metadata"]

        result = self.syntax.parse_block(candidate)
        assert result.success
        assert result.metadata  # Empty metadata object
        assert result.content
        assert result.content.text == "Just content\nNo metadata"


class TestDelimiterFrontmatterSyntax:
    """Tests for delimiter frontmatter syntax parser."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.syntax = DelimiterFrontmatterSyntax(
            metadata_class=TestDelimiterMetadata,
            content_class=TestDelimiterContent,
        )

    def test_detect_start_delimiter(self) -> None:
        """Test detection of start delimiter."""
        result = self.syntax.detect_line("!!start", None)
        assert result.is_opening
        assert not result.is_closing

    def test_detect_end_delimiter(self) -> None:
        """Test detection of end delimiter."""
        candidate = BlockCandidate(syntax=self.syntax, start_line=1)
        candidate.state = BlockState.ACCUMULATING_CONTENT

        result = self.syntax.detect_line("!!end", candidate)
        assert result.is_closing

    def test_parse_full_block(self) -> None:
        """Test parsing a complete delimiter frontmatter block."""
        candidate = BlockCandidate(syntax=self.syntax, start_line=1)
        candidate.state = BlockState.COMPLETED
        candidate.lines = [
            "!!start",
            "---",
            "id: patch01",
            "name: fix",
            "path: main.py",
            "---",
            "@@ -10,3 +10,5 @@",
            " def main():",
            "     print('Hello')",
            "+    print('World')",
            "+    return 0",
            "!!end",
        ]
        candidate.metadata_lines = [
            "id: patch01",
            "name: fix",
            "path: main.py",
        ]
        candidate.content_lines = [
            "@@ -10,3 +10,5 @@",
            " def main():",
            "     print('Hello')",
            "+    print('World')",
            "+    return 0",
        ]

        result = self.syntax.parse_block(candidate)
        assert result.success
        assert result.metadata
        assert result.metadata.id == "patch01"
        assert result.metadata.name == "fix"
        assert result.metadata.path == "main.py"
        assert result.content
        # Using parse method
        expected_content = "\n".join(candidate.content_lines)
        assert result.content.raw == expected_content

    def test_custom_delimiters(self) -> None:
        """Test using custom start/end delimiters."""
        custom_syntax = DelimiterFrontmatterSyntax(
            metadata_class=TestDelimiterMetadata,
            content_class=TestDelimiterContent,
            start_delimiter="<<<BEGIN>>>",
            end_delimiter="<<<END>>>",
        )

        # Test opening detection
        result = custom_syntax.detect_line("<<<BEGIN>>>", None)
        assert result.is_opening

        # Test closing detection
        candidate = BlockCandidate(syntax=custom_syntax, start_line=1)
        candidate.state = BlockState.ACCUMULATING_CONTENT
        result = custom_syntax.detect_line("<<<END>>>", candidate)
        assert result.is_closing
