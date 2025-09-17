"""Tests for built-in syntax implementations."""


from streamblocks.core.models import BlockCandidate
from streamblocks.core.types import BlockState
from streamblocks.syntaxes.builtin import (
    DelimiterBlockSyntax,
    MarkdownCodeSyntax,
    YAMLFrontmatterSyntax,
)


class TestYAMLFrontmatterSyntax:
    """Tests for YAML frontmatter syntax parser."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.syntax = YAMLFrontmatterSyntax()

    def test_detect_opening_delimiter(self) -> None:
        """Test detection of opening delimiter."""
        result = self.syntax.detect_line("---", None)
        assert result.is_opening
        assert not result.is_closing

    def test_detect_closing_delimiter_in_metadata(self) -> None:
        """Test detection of closing delimiter in metadata state."""
        candidate = BlockCandidate(syntax=self.syntax, start_line=1)
        candidate.state = BlockState.ACCUMULATING_METADATA
        candidate.lines = ["---"]
        candidate.metadata_lines = []
        candidate.content_lines = []
        result = self.syntax.detect_line("---", candidate)
        assert result.is_metadata_boundary
        assert not result.is_closing

    def test_parse_simple_frontmatter(self) -> None:
        """Test parsing simple YAML frontmatter."""
        candidate = BlockCandidate(syntax=self.syntax, start_line=1)
        candidate.state = BlockState.COMPLETED
        candidate.lines = ["---", "title: Test Document", "type: article", "---", "# Content", "Hello world"]
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
        candidate.lines = ["---", "tags: [python, testing]", "custom_field: value", "---", "Content"]
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
        candidate.lines = ["---", "---", "Just content"]
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
        candidate.lines = ["---", "invalid: yaml: syntax:", "---"]
        candidate.metadata_lines = ["invalid: yaml: syntax:"]
        candidate.content_lines = []

        result = self.syntax.parse_block(candidate)
        assert not result.success
        assert "Invalid YAML" in result.error


class TestDelimiterBlockSyntax:
    """Tests for delimiter block syntax parser."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.syntax = DelimiterBlockSyntax()

    def test_detect_opening_with_metadata(self) -> None:
        """Test detection of opening delimiter with inline metadata."""
        result = self.syntax.detect_line("!!block123:shell:bash", None)
        assert result.is_opening
        assert result.metadata
        assert result.metadata["hash_id"] == "block123"
        assert result.metadata["block_type"] == "shell"
        assert result.metadata["params"] == "bash"

    def test_detect_closing_delimiter(self) -> None:
        """Test detection of closing delimiter."""
        candidate = BlockCandidate(syntax=self.syntax, start_line=1)
        candidate.state = BlockState.ACCUMULATING_CONTENT
        candidate.lines = ["!!block123:shell"]
        candidate.metadata_lines = []
        candidate.content_lines = ["echo test"]
        candidate.metadata = {"hash_id": "block123"}
        result = self.syntax.detect_line("!!block123:end", candidate)
        assert result.is_closing

    def test_parse_simple_block(self) -> None:
        """Test parsing simple delimiter block."""
        candidate = BlockCandidate(syntax=self.syntax, start_line=1)
        candidate.state = BlockState.COMPLETED
        candidate.lines = ["!!abc123:python", "print('Hello')", "!!abc123:end"]
        candidate.metadata_lines = []
        candidate.content_lines = ["print('Hello')"]
        candidate.metadata = {"hash_id": "abc123", "block_type": "python"}

        result = self.syntax.parse_block(candidate)
        assert result.success
        assert result.metadata
        assert result.metadata.hash_id == "abc123"
        assert result.metadata.block_type == "python"
        assert result.content
        assert result.content.text == "print('Hello')"

    def test_extract_inline_metadata_variations(self) -> None:
        """Test various inline metadata formats."""
        # Simple format
        meta = self.syntax._extract_inline_metadata("!!block123")
        assert meta["hash_id"] == "block123"

        # With type
        meta = self.syntax._extract_inline_metadata("!!block123:code")
        assert meta["hash_id"] == "block123"
        assert meta["block_type"] == "code"

        # With type and params
        meta = self.syntax._extract_inline_metadata("!!block123:shell:bash")
        assert meta["hash_id"] == "block123"
        assert meta["block_type"] == "shell"
        assert meta["params"] == "bash"

    def test_invalid_hash_id(self) -> None:
        """Test validation of invalid hash IDs."""
        candidate = BlockCandidate(syntax=self.syntax, start_line=1)
        candidate.state = BlockState.COMPLETED
        candidate.lines = ["!!invalid hash:code", "content", "!!invalid hash:end"]
        candidate.metadata_lines = []
        candidate.content_lines = ["content"]
        candidate.metadata = {"hash_id": "invalid hash", "block_type": "code"}

        result = self.syntax.parse_block(candidate)
        assert not result.success


class TestMarkdownCodeSyntax:
    """Tests for markdown code syntax parser."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.syntax = MarkdownCodeSyntax()

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
        assert result.content.code == "def hello():\n    print('Hello')"
        assert result.content.line_count == 2

    def test_parse_with_filename(self) -> None:
        """Test parsing code block with filename."""
        result = self.syntax.detect_line("```javascript app.js", None)
        assert result.metadata["language"] == "javascript"
        assert result.metadata["filename"] == "app.js"

    def test_parse_info_string_variations(self) -> None:
        """Test parsing various info string formats."""
        # With attributes
        meta = self.syntax._parse_info_string("python {highlight: [1, 2, 3]}")
        assert meta["language"] == "python"
        assert meta["highlight_lines"] == [1, 2, 3]

        # With filename and attributes
        meta = self.syntax._parse_info_string("javascript app.js {title: 'Example'}")
        assert meta["language"] == "javascript"
        assert meta["filename"] == "app.js"
        assert meta["title"] == "Example"

        # With line numbers
        meta = self.syntax._parse_info_string("python {line-numbers: true}")
        assert meta["language"] == "python"
        assert meta["line_numbers"] is True

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
        assert result.content.code == ""
        assert result.content.line_count == 0
