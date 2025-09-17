"""Tests for content models."""

import pytest
from pydantic import ValidationError

from streamblocks.content import (
    FileOperation,
    FileOperationsContent,
    FileOperationsMetadata,
    PatchContent,
    PatchMetadata,
)

# Test constants
EXPECTED_OPERATIONS_COUNT = 3
EXPECTED_OPERATIONS_WITH_EMPTY_LINES = 2


class TestFileOperationsContent:
    """Tests for FileOperationsContent."""

    def test_parse_valid_operations(self):
        """Test parsing valid file operations."""
        text = """
        src/main.py:E
        src/utils.py:C
        old/legacy.py:D
        """

        content = FileOperationsContent.parse(text)

        assert len(content.operations) == EXPECTED_OPERATIONS_COUNT

        assert content.operations[0].path == "src/main.py"
        assert content.operations[0].action == "edit"

        assert content.operations[1].path == "src/utils.py"
        assert content.operations[1].action == "create"

        assert content.operations[2].path == "old/legacy.py"
        assert content.operations[2].action == "delete"

    def test_parse_with_empty_lines(self):
        """Test parsing handles empty lines."""
        text = """

        file1.txt:C

        file2.txt:E

        """

        content = FileOperationsContent.parse(text)

        assert len(content.operations) == EXPECTED_OPERATIONS_WITH_EMPTY_LINES
        assert content.operations[0].path == "file1.txt"
        assert content.operations[1].path == "file2.txt"

    def test_parse_lowercase_actions(self):
        """Test parsing handles lowercase action codes."""
        text = """
        file1.txt:c
        file2.txt:e
        file3.txt:d
        """

        content = FileOperationsContent.parse(text)

        assert content.operations[0].action == "create"
        assert content.operations[1].action == "edit"
        assert content.operations[2].action == "delete"

    def test_parse_paths_with_colons(self):
        """Test parsing handles paths containing colons."""
        text = "C:/Users/test/file.txt:E"

        content = FileOperationsContent.parse(text)

        assert len(content.operations) == 1
        assert content.operations[0].path == "C:/Users/test/file.txt"
        assert content.operations[0].action == "edit"

    def test_parse_invalid_format(self):
        """Test parsing raises error for invalid format."""
        text = "invalid_line_without_colon"

        with pytest.raises(ValueError) as exc_info:
            FileOperationsContent.parse(text)

        assert "Invalid file operation format" in str(exc_info.value)

    def test_parse_invalid_action_code(self):
        """Test parsing raises error for invalid action code."""
        text = "file.txt:X"

        with pytest.raises(ValueError) as exc_info:
            FileOperationsContent.parse(text)

        assert "Unknown action code: X" in str(exc_info.value)

    def test_parse_empty_text(self):
        """Test parsing empty text returns no operations."""
        content = FileOperationsContent.parse("")
        assert content.operations == []

    def test_file_operation_model(self):
        """Test FileOperation model directly."""
        op = FileOperation(action="create", path="/path/to/file.txt")

        assert op.action == "create"
        assert op.path == "/path/to/file.txt"

        # Test validation of action
        with pytest.raises(ValueError):
            FileOperation(action="invalid", path="/path")  # type: ignore


class TestFileOperationsMetadata:
    """Tests for FileOperationsMetadata."""

    def test_metadata_creation(self):
        """Test creating metadata with required fields."""
        metadata = FileOperationsMetadata(id="test123")

        assert metadata.id == "test123"
        assert metadata.block_type == "files_operations"
        assert metadata.description is None

    def test_metadata_with_description(self):
        """Test metadata with optional description."""
        metadata = FileOperationsMetadata(id="test123", description="Update configuration files")

        assert metadata.id == "test123"
        assert metadata.description == "Update configuration files"

    def test_metadata_serialization(self):
        """Test metadata can be serialized."""
        metadata = FileOperationsMetadata(id="test123", description="Test description")

        data = metadata.model_dump()

        assert data["id"] == "test123"
        assert data["block_type"] == "files_operations"
        assert data["description"] == "Test description"


class TestPatchContent:
    """Tests for PatchContent."""

    def test_parse_valid_diff(self):
        """Test parsing valid unified diff."""
        diff = """
--- a/file.txt
+++ b/file.txt
@@ -1,3 +1,3 @@
 line 1
-old line 2
+new line 2
 line 3
"""

        content = PatchContent.parse(diff)
        assert content.diff == diff

    def test_parse_multiple_hunks(self):
        """Test parsing diff with multiple hunks."""
        diff = """
@@ -1,3 +1,3 @@
 line 1
-old line
+new line
@@ -10,3 +10,3 @@
 another section
-old content
+new content
"""

        content = PatchContent.parse(diff)
        assert "@@ -1,3 +1,3 @@" in content.diff
        assert "@@ -10,3 +10,3 @@" in content.diff

    def test_parse_empty_diff(self):
        """Test parsing empty diff raises error."""
        with pytest.raises(ValueError) as exc_info:
            PatchContent.parse("")

        assert "Diff content cannot be empty" in str(exc_info.value)

    def test_parse_invalid_diff_no_markers(self):
        """Test parsing diff without @@ markers raises error."""
        diff = """
Just some text
without any diff markers
"""

        with pytest.raises(ValueError) as exc_info:
            PatchContent.parse(diff)

        assert "missing @@ range markers" in str(exc_info.value)

    def test_direct_creation_with_validation(self):
        """Test creating PatchContent directly triggers validation."""
        # Valid diff
        valid_diff = "@@ -1,1 +1,1 @@\n-old\n+new"
        content = PatchContent(diff=valid_diff)
        assert content.diff == valid_diff

        # Invalid diff
        with pytest.raises(ValueError) as exc_info:
            PatchContent(diff="no markers here")

        assert "missing @@ range markers" in str(exc_info.value)


class TestPatchMetadata:
    """Tests for PatchMetadata."""

    def test_metadata_creation(self):
        """Test creating patch metadata."""
        metadata = PatchMetadata(id="patch123", file_path="src/main.py")

        assert metadata.id == "patch123"
        assert metadata.block_type == "patch"
        assert metadata.file_path == "src/main.py"
        assert metadata.description is None

    def test_metadata_with_description(self):
        """Test patch metadata with description."""
        metadata = PatchMetadata(id="patch123", file_path="src/main.py", description="Fix typo in function name")

        assert metadata.description == "Fix typo in function name"

    def test_metadata_requires_file_path(self):
        """Test that file_path is required."""
        with pytest.raises(ValidationError):
            PatchMetadata(id="patch123", file_path=None)  # type: ignore  # Test invalid file_path
