"""Tests for built-in syntax implementations with hardcoded models (legacy).

NOTE: This test file uses the old approach with hardcoded models.
See test_generic_syntaxes.py for the new approach with user-provided models.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from streamblocks.core.models import BlockCandidate
from streamblocks.core.types import BlockState
from streamblocks.syntaxes.builtin import (
    DelimiterFrontmatterSyntax,
    DelimiterPreambleSyntax,
    MarkdownFrontmatterSyntax,
)


# Legacy test models (matching the old hardcoded models)
class YAMLMetadata(BaseModel):
    """Metadata model for YAML frontmatter blocks."""

    model_config = ConfigDict(extra="allow", validate_assignment=True)

    id: str | None = Field(None, description="Optional block identifier")
    type: str | None = Field(None, description="Block type or category")
    title: str | None = Field(None, description="Block title")
    author: str | None = Field(None, description="Block author")
    tags: list[str] = Field(default_factory=list, description="Block tags")
    extra_fields: dict[str, Any] = Field(default_factory=dict, description="Additional fields")

    def __init__(self, **data: Any) -> None:
        """Initialize with dynamic field handling."""
        # Known fields
        known_fields = {"id", "type", "title", "author", "tags"}

        # Separate known and extra fields
        known_data = {k: v for k, v in data.items() if k in known_fields}
        extra_data = {k: v for k, v in data.items() if k not in known_fields}

        # Initialize with known fields
        super().__init__(**known_data)

        # Store extra fields
        self.extra_fields = extra_data


class YAMLContent(BaseModel):
    """Content model for YAML frontmatter blocks."""

    model_config = ConfigDict(validate_assignment=True)

    text: str = Field(description="The content text")
    format: str = Field(default="markdown", description="Content format")

    @property
    def lines(self) -> list[str]:
        """Get content as list of lines."""
        return self.text.splitlines()

    @property
    def is_empty(self) -> bool:
        """Check if content is empty."""
        return not self.text.strip()


class DelimiterMetadata(BaseModel):
    """Metadata model for delimiter-based blocks."""

    model_config = ConfigDict(validate_assignment=True)

    hash_id: str = Field(description="Block hash identifier")
    block_type: str = Field(default="block", description="Block type")
    params: str | None = Field(None, description="Optional parameters")
    language: str | None = Field(None, description="Language hint for code blocks")
    attributes: dict[str, str] = Field(default_factory=dict, description="Additional attributes")


class DelimiterContent(BaseModel):
    """Content model for delimiter-based blocks."""

    model_config = ConfigDict(validate_assignment=True)

    text: str = Field(description="The content text")
    is_code: bool = Field(default=False, description="Whether content is code")
    line_count: int = Field(default=0, description="Number of content lines")

    def __init__(self, **data: Any) -> None:
        """Initialize with computed fields."""
        super().__init__(**data)
        if "line_count" not in data and "text" in data:
            self.line_count = len(data["text"].splitlines())


class MarkdownCodeMetadata(BaseModel):
    """Metadata model for markdown code blocks."""

    model_config = ConfigDict(validate_assignment=True)

    language: str | None = Field(None, description="Programming language")
    filename: str | None = Field(None, description="Optional filename")
    title: str | None = Field(None, description="Optional title")
    line_numbers: bool = Field(False, description="Whether to show line numbers")
    highlight_lines: list[int] = Field(default_factory=list, description="Lines to highlight")
    attributes: dict[str, str] = Field(default_factory=dict, description="Additional attributes")


class MarkdownCodeContent(BaseModel):
    """Content model for markdown code blocks."""

    model_config = ConfigDict(validate_assignment=True)

    code: str = Field(description="The code content")
    line_count: int = Field(default=0, description="Number of lines")
    has_trailing_newline: bool = Field(True, description="Whether code ends with newline")

    def __init__(self, **data: Any) -> None:
        """Initialize with computed fields."""
        super().__init__(**data)
        if "line_count" not in data and "code" in data:
            self.line_count = len(data["code"].splitlines())
        if "has_trailing_newline" not in data and "code" in data:
            self.has_trailing_newline = data["code"].endswith("\n")


class TestDelimiterFrontmatterSyntax:
    """Tests for delimiter frontmatter syntax parser (formerly YAML frontmatter)."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.syntax = DelimiterFrontmatterSyntax(
            metadata_class=YAMLMetadata,
            content_class=YAMLContent,
        )

    def test_detect_opening_delimiter(self) -> None:
        """Test detection of opening delimiter."""
        result = self.syntax.detect_line("!!start", None)
        assert result.is_opening
        assert not result.is_closing

    def test_detect_closing_delimiter(self) -> None:
        """Test detection of closing delimiter."""
        candidate = BlockCandidate(syntax=self.syntax, start_line=1)
        candidate.state = BlockState.ACCUMULATING_CONTENT
        candidate.lines = ["!!start", "---", "title: Test", "---", "content"]
        candidate.metadata_lines = ["title: Test"]
        candidate.content_lines = ["content"]
        result = self.syntax.detect_line("!!end", candidate)
        assert result.is_closing

    def test_parse_simple_frontmatter(self) -> None:
        """Test parsing simple YAML frontmatter."""
        candidate = BlockCandidate(syntax=self.syntax, start_line=1)
        candidate.state = BlockState.COMPLETED
        candidate.lines = [
            "!!start",
            "---",
            "title: Test Document",
            "type: article",
            "---",
            "# Content",
            "Hello world",
            "!!end",
        ]
        candidate.metadata_lines = ["title: Test Document", "type: article"]
        candidate.content_lines = ["# Content", "Hello world"]

        result = self.syntax.parse_block(candidate)
        assert result.success
        assert result.metadata
        assert result.metadata.title == "Test Document"
        assert result.metadata.type == "article"
        assert result.content
        assert result.content.text == "# Content\nHello world"

    def test_parse_with_tags_and_extra_fields(self) -> None:
        """Test parsing with tags and extra fields."""
        candidate = BlockCandidate(syntax=self.syntax, start_line=1)
        candidate.state = BlockState.COMPLETED
        candidate.lines = [
            "!!start",
            "---",
            "tags: [python, testing]",
            "custom_field: value",
            "---",
            "Content",
            "!!end",
        ]
        candidate.metadata_lines = ["tags: [python, testing]", "custom_field: value"]
        candidate.content_lines = ["Content"]

        result = self.syntax.parse_block(candidate)
        assert result.success
        assert result.metadata
        assert result.metadata.tags == ["python", "testing"]
        assert result.metadata.extra_fields["custom_field"] == "value"

    def test_empty_metadata_section(self) -> None:
        """Test handling empty metadata section."""
        candidate = BlockCandidate(syntax=self.syntax, start_line=1)
        candidate.state = BlockState.COMPLETED
        candidate.lines = ["!!start", "---", "---", "Just content", "!!end"]
        candidate.metadata_lines = []
        candidate.content_lines = ["Just content"]

        result = self.syntax.parse_block(candidate)
        assert result.success
        assert result.content
        assert result.content.text == "Just content"

    def test_invalid_yaml_metadata(self) -> None:
        """Test handling of invalid YAML metadata."""
        candidate = BlockCandidate(syntax=self.syntax, start_line=1)
        candidate.state = BlockState.COMPLETED
        candidate.lines = ["!!start", "---", "invalid: yaml: syntax:", "---", "!!end"]
        candidate.metadata_lines = ["invalid: yaml: syntax:"]
        candidate.content_lines = []

        result = self.syntax.parse_block(candidate)
        assert not result.success
        assert result.error is not None
        assert "Invalid YAML" in result.error


class TestDelimiterPreambleSyntax:
    """Tests for delimiter preamble syntax parser."""

    def setup_method(self) -> None:
        """Set up test fixtures."""

        # Need to define metadata for delimiter preamble
        class PreambleMetadata(BaseModel):
            id: str = Field(description="Block ID")
            type: str = Field(default="block", description="Block type")

        self.syntax = DelimiterPreambleSyntax(
            metadata_class=PreambleMetadata,
            content_class=DelimiterContent,
        )

    def test_detect_opening_with_metadata(self) -> None:
        """Test detection of opening delimiter with inline metadata."""
        result = self.syntax.detect_line("!!block123:shell", None)
        assert result.is_opening
        assert result.metadata
        assert "_raw_preamble" in result.metadata
        assert result.metadata["_raw_preamble"] == "block123:shell"

    def test_detect_closing_delimiter(self) -> None:
        """Test detection of closing delimiter."""
        candidate = BlockCandidate(syntax=self.syntax, start_line=1)
        candidate.state = BlockState.ACCUMULATING_CONTENT
        candidate.lines = ["!!block123:shell"]
        candidate.metadata_lines = []
        candidate.content_lines = ["echo test"]
        result = self.syntax.detect_line("!!end", candidate)
        assert result.is_closing

    def test_parse_simple_block(self) -> None:
        """Test parsing simple delimiter block."""
        candidate = BlockCandidate(syntax=self.syntax, start_line=1)
        candidate.state = BlockState.COMPLETED
        candidate.lines = ["!!abc123:python", "print('Hello')", "!!end"]
        candidate.metadata_lines = []
        candidate.content_lines = ["print('Hello')"]
        candidate.metadata = {"_raw_preamble": "abc123:python"}

        result = self.syntax.parse_block(candidate)
        assert result.success
        assert result.metadata
        assert result.metadata.id == "abc123"
        assert result.metadata.type == "python"
        assert result.content
        assert result.content.text == "print('Hello')"

    def test_parse_preamble(self) -> None:
        """Test preamble parsing."""
        candidate = BlockCandidate(syntax=self.syntax, start_line=1)
        candidate.state = BlockState.COMPLETED
        candidate.lines = ["!!test123:block", "content", "!!end"]
        candidate.metadata_lines = []
        candidate.content_lines = ["content"]
        candidate.metadata = {"_raw_preamble": "test123:block"}

        result = self.syntax.parse_block(candidate)
        assert result.success
        assert result.metadata is not None
        assert result.metadata.id == "test123"
        assert result.metadata.type == "block"


class TestMarkdownFrontmatterSyntaxRenamed:
    """Tests for markdown frontmatter syntax parser (formerly markdown code)."""

    def setup_method(self) -> None:
        """Set up test fixtures."""

        # Define test metadata/content models
        class MarkdownMetadata(BaseModel):
            id: str | None = None
            type: str | None = None
            language: str | None = None

        class MarkdownContent(BaseModel):
            text: str

        self.syntax = MarkdownFrontmatterSyntax(
            metadata_class=MarkdownMetadata,
            content_class=MarkdownContent,
        )

    def test_detect_opening_fence(self) -> None:
        """Test detection of opening code fence."""
        result = self.syntax.detect_line("```python", None)
        assert result.is_opening
        assert result.metadata
        assert result.metadata["language"] == "python"

    def test_detect_closing_fence(self) -> None:
        """Test detection of closing code fence."""
        candidate = BlockCandidate(syntax=self.syntax, start_line=1)
        candidate.state = BlockState.ACCUMULATING_CONTENT
        candidate.lines = ["```python"]
        candidate.metadata_lines = []
        candidate.content_lines = ["print('test')"]
        result = self.syntax.detect_line("```", candidate)
        assert result.is_closing

    def test_parse_simple_code_block(self) -> None:
        """Test parsing simple code block."""
        candidate = BlockCandidate(syntax=self.syntax, start_line=1)
        candidate.state = BlockState.COMPLETED
        candidate.lines = ["```python", "def hello():", "    print('Hello')", "```"]
        candidate.metadata_lines = []
        candidate.content_lines = ["def hello():", "    print('Hello')"]
        candidate.metadata = {"language": "python"}

        result = self.syntax.parse_block(candidate)
        assert result.success
        assert result.metadata
        assert result.metadata.language == "python"
        assert result.content
        assert result.content.text == "def hello():\n    print('Hello')"
        # Note: line_count was part of old MarkdownCodeContent, not the generic model

    def test_detect_without_metadata(self) -> None:
        """Test detection without inline metadata."""
        # MarkdownFrontmatterSyntax doesn't extract metadata from opening line
        result = self.syntax.detect_line("```javascript app.js", None)
        assert result.is_opening
        assert result.metadata is None  # No inline metadata in this syntax

    def test_empty_code_block(self) -> None:
        """Test handling empty code block."""
        candidate = BlockCandidate(syntax=self.syntax, start_line=1)
        candidate.state = BlockState.COMPLETED
        candidate.lines = ["```", "```"]
        candidate.metadata_lines = []
        candidate.content_lines = []
        candidate.metadata = {}

        result = self.syntax.parse_block(candidate)
        assert result.success
        assert result.content
        assert result.content.text == ""
