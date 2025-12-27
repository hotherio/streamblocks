"""Tests for patch block models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hother.streamblocks_examples.blocks.agent.patch import Patch, PatchContent, PatchMetadata


class TestPatchMetadata:
    """Tests for PatchMetadata model."""

    def test_metadata_with_required_fields(self) -> None:
        """Test creating metadata with required fields."""
        metadata = PatchMetadata(
            id="patch-1",
            file="src/main.py",
        )

        assert metadata.id == "patch-1"
        assert metadata.block_type == "patch"  # Default value
        assert metadata.file == "src/main.py"
        assert metadata.start_line is None
        assert metadata.author is None
        assert metadata.priority is None
        assert metadata.description is None

    def test_metadata_with_all_fields(self) -> None:
        """Test creating metadata with all fields."""
        metadata = PatchMetadata(
            id="patch-2",
            file="lib/utils.py",
            start_line=42,
            author="developer",
            priority="high",
            description="Fix critical bug",
        )

        assert metadata.file == "lib/utils.py"
        assert metadata.start_line == 42
        assert metadata.author == "developer"
        assert metadata.priority == "high"
        assert metadata.description == "Fix critical bug"

    def test_metadata_block_type_default(self) -> None:
        """Test that block_type defaults to 'patch'."""
        metadata = PatchMetadata(
            id="patch-3",
            file="test.py",
        )

        assert metadata.block_type == "patch"

    def test_metadata_missing_required_file(self) -> None:
        """Test that missing file raises validation error."""
        with pytest.raises(ValidationError):
            PatchMetadata(id="patch-4")  # type: ignore[call-arg]


class TestPatchContentParse:
    """Tests for PatchContent.parse() method."""

    def test_parse_empty_patch_raises_error(self) -> None:
        """Test that empty patch raises ValueError."""
        with pytest.raises(ValueError, match="Empty patch"):
            PatchContent.parse("")

    def test_parse_whitespace_only_raises_error(self) -> None:
        """Test that whitespace-only patch raises ValueError."""
        with pytest.raises(ValueError, match="Empty patch"):
            PatchContent.parse("   \n\t  \n  ")

    def test_parse_valid_unified_diff(self) -> None:
        """Test parsing valid unified diff format."""
        diff_text = """+++ a/file.py
--- b/file.py
@@ -1,3 +1,4 @@
 def hello():
+    print("hello")
     return None
"""
        content = PatchContent.parse(diff_text)

        assert content.raw_content == diff_text
        assert content.diff == diff_text.strip()

    def test_parse_diff_with_additions(self) -> None:
        """Test parsing diff with added lines."""
        diff_text = """+line1
+line2
+line3"""
        content = PatchContent.parse(diff_text)

        assert content.diff == diff_text.strip()

    def test_parse_diff_with_deletions(self) -> None:
        """Test parsing diff with deleted lines."""
        diff_text = """-removed line 1
-removed line 2"""
        content = PatchContent.parse(diff_text)

        assert content.diff == diff_text.strip()

    def test_parse_diff_with_context(self) -> None:
        """Test parsing diff with context lines (space-prefixed)."""
        diff_text = """ context line
+added line
 more context
-deleted line
 final context"""
        content = PatchContent.parse(diff_text)

        assert content.diff == diff_text.strip()

    def test_parse_content_without_diff_markers(self) -> None:
        """Test parsing content without standard diff markers.

        The parser accepts content without explicit diff markers,
        allowing for more flexible patch formats.
        """
        content_text = """def hello():
    print("hello world")
"""
        content = PatchContent.parse(content_text)

        assert content.raw_content == content_text
        assert content.diff == content_text.strip()

    def test_parse_content_no_diff_markers_at_all(self) -> None:
        """Test parsing content with NO lines starting with +, -, or space.

        This covers line 32 of patch.py (has_diff_lines = False branch).
        """
        # Content where NO line starts with +, -, or space
        content_text = "header_line\nanother_line\nfinal_line"
        content = PatchContent.parse(content_text)

        assert content.raw_content == content_text
        assert content.diff == content_text.strip()

    def test_parse_mixed_content(self) -> None:
        """Test parsing content with some lines having markers and some not."""
        mixed_text = """header line
+added
normal line
-removed
footer"""
        content = PatchContent.parse(mixed_text)

        assert content.diff == mixed_text.strip()

    def test_parse_preserves_whitespace(self) -> None:
        """Test that parse preserves internal whitespace."""
        diff_text = """+    indented line
+        deeply indented"""
        content = PatchContent.parse(diff_text)

        assert "+    indented line" in content.diff
        assert "+        deeply indented" in content.diff


class TestPatchContentModel:
    """Tests for PatchContent model validation."""

    def test_content_requires_diff(self) -> None:
        """Test that diff field is required."""
        with pytest.raises(ValidationError):
            PatchContent(raw_content="test")  # type: ignore[call-arg]

    def test_content_with_both_fields(self) -> None:
        """Test content with both raw_content and diff."""
        content = PatchContent(
            raw_content="original",
            diff="+modified",
        )

        assert content.raw_content == "original"
        assert content.diff == "+modified"


class TestPatchBlock:
    """Tests for Patch block type."""

    def test_patch_type_exists(self) -> None:
        """Test that Patch type alias is available."""
        assert Patch is not None

    def test_patch_can_be_created(self) -> None:
        """Test creating a complete Patch block."""
        metadata = PatchMetadata(
            id="test-patch",
            file="example.py",
            start_line=10,
        )
        content = PatchContent(
            raw_content="+new line",
            diff="+new line",
        )

        block = Patch(metadata=metadata, content=content)

        assert block.metadata.file == "example.py"
        assert block.metadata.start_line == 10
        assert block.content.diff == "+new line"

    def test_patch_with_full_metadata(self) -> None:
        """Test creating Patch block with full metadata."""
        metadata = PatchMetadata(
            id="full-patch",
            file="src/app.py",
            start_line=100,
            author="Alice",
            priority="medium",
            description="Add logging",
        )
        content = PatchContent.parse("+import logging\n+logger = logging.getLogger(__name__)")

        block = Patch(metadata=metadata, content=content)

        assert block.metadata.author == "Alice"
        assert block.metadata.description == "Add logging"
        assert "logging" in block.content.diff
