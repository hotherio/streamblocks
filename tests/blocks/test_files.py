"""Tests for file operations block models."""

from __future__ import annotations

import pytest

from hother.streamblocks_examples.blocks.agent.files import (
    FileContentContent,
    FileOperation,
    FileOperationsContent,
)


class TestFileOperation:
    """Tests for FileOperation model."""

    def test_create_operation(self) -> None:
        """Test creating a file operation."""
        op = FileOperation(action="create", path="test.py")
        assert op.action == "create"
        assert op.path == "test.py"

    def test_all_action_types(self) -> None:
        """Test all valid action types."""
        for action in ["create", "edit", "delete"]:
            op = FileOperation(action=action, path="file.py")  # type: ignore[arg-type]
            assert op.action == action


class TestFileOperationsContentParse:
    """Tests for FileOperationsContent.parse()."""

    def test_parse_single_operation(self) -> None:
        """Test parsing a single file operation."""
        content = FileOperationsContent.parse("file.py:C")
        assert len(content.operations) == 1
        assert content.operations[0].path == "file.py"
        assert content.operations[0].action == "create"

    def test_parse_multiple_operations(self) -> None:
        """Test parsing multiple file operations."""
        raw = "file1.py:C\nfile2.py:E\nfile3.py:D"
        content = FileOperationsContent.parse(raw)
        assert len(content.operations) == 3
        assert content.operations[0].action == "create"
        assert content.operations[1].action == "edit"
        assert content.operations[2].action == "delete"

    def test_parse_skips_empty_lines(self) -> None:
        """Test that empty lines are skipped."""
        raw = "file1.py:C\n\nfile2.py:E"
        content = FileOperationsContent.parse(raw)
        assert len(content.operations) == 2

    def test_parse_lowercase_actions(self) -> None:
        """Test parsing with lowercase action codes."""
        raw = "file.py:c"
        content = FileOperationsContent.parse(raw)
        assert content.operations[0].action == "create"

    def test_parse_missing_colon_raises_error(self) -> None:
        """Test that missing colon raises ValueError.

        This covers lines 48-49.
        """
        with pytest.raises(ValueError, match="Invalid format"):
            FileOperationsContent.parse("file.py")

    def test_parse_unknown_action_raises_error(self) -> None:
        """Test that unknown action raises ValueError.

        This covers lines 55-56.
        """
        with pytest.raises(ValueError, match="Unknown action"):
            FileOperationsContent.parse("file.py:X")

    def test_parse_stores_raw_content(self) -> None:
        """Test that raw content is stored."""
        raw = "file.py:C"
        content = FileOperationsContent.parse(raw)
        assert content.raw_content == raw

    def test_parse_path_with_colon(self) -> None:
        """Test parsing paths that contain colons (like Windows paths)."""
        raw = "C:\\path\\to\\file.py:C"
        content = FileOperationsContent.parse(raw)
        assert content.operations[0].path == "C:\\path\\to\\file.py"
        assert content.operations[0].action == "create"


class TestFileContentContentParse:
    """Tests for FileContentContent.parse()."""

    def test_parse_stores_raw_text(self) -> None:
        """Test that parse stores raw text.

        This covers line 97.
        """
        raw = "def hello():\n    print('Hello')"
        content = FileContentContent.parse(raw)
        assert content.raw_content == raw

    def test_parse_empty_content(self) -> None:
        """Test parsing empty content."""
        content = FileContentContent.parse("")
        assert content.raw_content == ""

    def test_parse_multiline_content(self) -> None:
        """Test parsing multiline file content."""
        raw = "line 1\nline 2\nline 3"
        content = FileContentContent.parse(raw)
        assert content.raw_content == raw
