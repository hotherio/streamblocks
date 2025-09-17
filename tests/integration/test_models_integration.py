"""Integration tests for models with real syntaxes."""

from streamblocks.content import (
    FileOperationsContent,
    FileOperationsMetadata,
    PatchContent,
    PatchMetadata,
)
from streamblocks.core import Block, BlockCandidate, BlockRegistry, BlockState
from streamblocks.core.types import DetectionResult, ParseResult

# Test constants
EXPECTED_OPERATIONS_COUNT = 3
EXPECTED_LINE_COUNT = 4
EXPECTED_REGISTRY_COUNT = 2
BLOCK_START_LINE = 100
BLOCK_END_LINE = 106
HIGH_PRIORITY = 10
MEDIUM_PRIORITY = 20


class FileOpsSyntax:
    """Example syntax for file operations blocks."""

    @property
    def name(self) -> str:
        return "file_ops"

    def detect_line(self, line: str, context: BlockCandidate | None = None) -> DetectionResult:
        """Detect file operations block markers."""
        if line.strip() == "!! files":
            return DetectionResult(is_opening=True)
        if line.strip() == "!!" and context and context.state != BlockState.SEARCHING:
            return DetectionResult(is_closing=True)
        if line.strip() == "---" and context:
            return DetectionResult(is_metadata_boundary=True)
        return DetectionResult()

    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        """Check if still accumulating metadata."""
        return candidate.state == BlockState.ACCUMULATING_METADATA

    def parse_block(self, candidate: BlockCandidate) -> ParseResult[FileOperationsMetadata, FileOperationsContent]:
        """Parse the block into metadata and content."""
        try:
            # Parse metadata from YAML-like format
            metadata_text = "\n".join(candidate.metadata_lines)
            metadata_dict: dict[str, str] = {}
            for line in metadata_text.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    metadata_dict[key.strip()] = value.strip()

            metadata = FileOperationsMetadata(
                id=metadata_dict.get("id", "unknown"), description=metadata_dict.get("description")
            )

            # Parse content
            content_text = "\n".join(candidate.content_lines)
            content = FileOperationsContent.parse(content_text)

            return ParseResult(success=True, metadata=metadata, content=content)
        except Exception as e:
            return ParseResult(success=False, error=str(e))

    def validate_block(self, metadata: FileOperationsMetadata, content: FileOperationsContent) -> bool:
        """Validate block."""
        return True

    def get_opening_pattern(self) -> str | None:
        """Get opening pattern."""
        return r"^!! files$"

    def get_closing_pattern(self) -> str | None:
        """Get closing pattern."""
        return r"^!!$"

    def supports_nested_blocks(self) -> bool:
        """Check nested blocks support."""
        return False

    def get_block_type_hints(self) -> list[str]:
        """Get block type hints."""
        return ["files_operations", "files"]


class TestModelsIntegration:
    """Integration tests for models working together."""

    def test_block_candidate_with_file_ops_syntax(self):
        """Test BlockCandidate with file operations syntax."""
        syntax = FileOpsSyntax()
        candidate = BlockCandidate(syntax, start_line=10)

        # Simulate block accumulation
        candidate.add_line("!! files")
        candidate.current_section = "metadata"
        candidate.state = BlockState.ACCUMULATING_METADATA

        candidate.add_line("id: update-config")
        candidate.add_line("description: Update configuration files")

        candidate.current_section = "content"
        candidate.state = BlockState.ACCUMULATING_CONTENT

        candidate.add_line("config/app.yaml:E")
        candidate.add_line("config/old.yaml:D")
        candidate.add_line("config/new.yaml:C")

        # Parse the block
        result = syntax.parse_block(candidate)

        assert result.success
        assert result.metadata is not None
        assert result.content is not None
        assert result.metadata.id == "update-config"
        assert result.metadata.description == "Update configuration files"
        assert len(result.content.operations) == EXPECTED_OPERATIONS_COUNT

    def test_block_creation_from_candidate(self):
        """Test creating Block from parsed BlockCandidate."""
        syntax = FileOpsSyntax()
        candidate = BlockCandidate(syntax, start_line=1)

        # Build candidate
        candidate.add_line("!! files")
        candidate.current_section = "metadata"
        candidate.add_line("id: test123")
        candidate.add_line("---")
        candidate.current_section = "content"
        candidate.add_line("src/main.py:E")
        # Don't add the closing !! to content

        # Parse block
        result = syntax.parse_block(candidate)
        assert result.success
        assert result.metadata is not None
        assert result.content is not None

        # Create Block
        block = Block[FileOperationsMetadata, FileOperationsContent](
            syntax_name=syntax.name,
            metadata=result.metadata,
            content=result.content,
            raw_text=candidate.raw_text,
            line_start=candidate.start_line,
            line_end=candidate.start_line + len(candidate.lines) - 1,
            hash_id=candidate.compute_hash(),
        )

        assert block.syntax_name == "file_ops"
        assert block.metadata.id == "test123"
        assert len(block.content.operations) == 1
        assert block.line_start == 1
        assert block.line_end == EXPECTED_LINE_COUNT  # 4 lines total (!! files, id:, ---, src/main.py:E)

    def test_registry_with_multiple_syntaxes(self):
        """Test registry managing multiple syntax types."""
        registry = BlockRegistry()

        # Create different syntax implementations
        file_ops_syntax = FileOpsSyntax()

        class PatchSyntax:
            @property
            def name(self) -> str:
                return "patch"

            def detect_line(self, line: str, context: BlockCandidate | None = None) -> DetectionResult:
                if line.strip() == "!! patch":
                    return DetectionResult(is_opening=True)
                return DetectionResult()

            def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
                return False

            def parse_block(self, candidate: BlockCandidate) -> ParseResult[PatchMetadata, PatchContent]:
                # Simplified parsing
                return ParseResult(
                    success=True,
                    metadata=PatchMetadata(id="test", file_path="test.py"),
                    content=PatchContent(diff="@@ -1,1 +1,1 @@\n-old\n+new"),
                )

            def validate_block(self, metadata: PatchMetadata, content: PatchContent) -> bool:
                return True

            def get_opening_pattern(self) -> str | None:
                return None

            def get_closing_pattern(self) -> str | None:
                return None

            def supports_nested_blocks(self) -> bool:
                return False

            def get_block_type_hints(self) -> list[str]:
                return []

        patch_syntax = PatchSyntax()

        # Register syntaxes
        registry.register_syntax(file_ops_syntax, block_types=["files_operations"], priority=HIGH_PRIORITY)
        registry.register_syntax(patch_syntax, block_types=["patch", "diff"], priority=MEDIUM_PRIORITY)

        # Test retrieval
        all_syntaxes = registry.get_syntaxes()
        assert len(all_syntaxes) == EXPECTED_REGISTRY_COUNT

        # Test by block type
        file_syntaxes = registry.get_syntaxes_for_block_type("files_operations")
        assert len(file_syntaxes) == 1
        assert file_syntaxes[0].name == "file_ops"

        patch_syntaxes = registry.get_syntaxes_for_block_type("patch")
        assert len(patch_syntaxes) == 1
        assert patch_syntaxes[0].name == "patch"

        # Test that patch syntax handles both types
        diff_syntaxes = registry.get_syntaxes_for_block_type("diff")
        assert len(diff_syntaxes) == 1
        assert diff_syntaxes[0].name == "patch"

    def test_end_to_end_block_processing(self):
        """Test complete flow from text to Block."""
        # Set up
        syntax = FileOpsSyntax()
        lines = [
            "!! files",
            "id: refactor-2024",
            "description: Major refactoring",
            "---",
            "src/old_module.py:D",
            "src/new_module.py:C",
            "src/main.py:E",
            "!!",
        ]

        # Process lines
        candidate = BlockCandidate(syntax, start_line=100)

        # Detect opening
        assert syntax.detect_line(lines[0]).is_opening
        candidate.add_line(lines[0])

        # Process metadata
        candidate.current_section = "metadata"
        candidate.state = BlockState.ACCUMULATING_METADATA
        candidate.add_line(lines[1])
        candidate.add_line(lines[2])

        # Detect boundary
        assert syntax.detect_line(lines[3], candidate).is_metadata_boundary
        candidate.add_line(lines[3])

        # Process content
        candidate.current_section = "content"
        candidate.state = BlockState.ACCUMULATING_CONTENT
        candidate.add_line(lines[4])
        candidate.add_line(lines[5])
        candidate.add_line(lines[6])

        # Detect closing but don't add to content
        assert syntax.detect_line(lines[7], candidate).is_closing
        candidate.state = BlockState.COMPLETED

        # Parse and create block
        result = syntax.parse_block(candidate)
        assert result.success
        assert result.metadata is not None
        assert result.content is not None

        block = Block[FileOperationsMetadata, FileOperationsContent](
            syntax_name=syntax.name,
            metadata=result.metadata,
            content=result.content,
            raw_text=candidate.raw_text,
            line_start=candidate.start_line,
            line_end=candidate.start_line + len(candidate.lines) - 1,
            hash_id=candidate.compute_hash(),
        )

        # Verify final block
        assert block.metadata.id == "refactor-2024"
        assert block.metadata.description == "Major refactoring"
        assert len(block.content.operations) == EXPECTED_OPERATIONS_COUNT
        assert block.content.operations[0].action == "delete"
        assert block.content.operations[1].action == "create"
        assert block.content.operations[2].action == "edit"
        assert block.line_start == BLOCK_START_LINE
        assert block.line_end == BLOCK_END_LINE  # Adjusted since we don't include closing !!
