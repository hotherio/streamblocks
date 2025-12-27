"""Tests for BlockStateMachine."""

import pytest

from hother.streamblocks import (
    DelimiterPreambleSyntax,
    Registry,
)
from hother.streamblocks.core.block_state_machine import BlockStateMachine
from hother.streamblocks.core.types import (
    BlockContentDeltaEvent,
    BlockContentEndEvent,
    BlockEndEvent,
    BlockErrorCode,
    BlockErrorEvent,
    BlockHeaderDeltaEvent,
    BlockStartEvent,
    EventType,
    TextContentEvent,
)
from hother.streamblocks_examples.blocks.agent import FileOperations


@pytest.fixture
def syntax() -> DelimiterPreambleSyntax:
    """Create a DelimiterPreambleSyntax instance."""
    return DelimiterPreambleSyntax()


@pytest.fixture
def registry(syntax: DelimiterPreambleSyntax) -> Registry:
    """Create a Registry with FileOperations registered."""
    reg = Registry(syntax=syntax)
    reg.register("files_operations", FileOperations)
    return reg


@pytest.fixture
def machine(syntax: DelimiterPreambleSyntax, registry: Registry) -> BlockStateMachine:
    """Create a BlockStateMachine instance."""
    return BlockStateMachine(syntax, registry)


class TestBlockStateMachineBasics:
    """Basic functionality tests for BlockStateMachine."""

    def test_initial_state(self, machine: BlockStateMachine) -> None:
        """Machine should start with no candidates."""
        assert machine.candidates == []
        assert not machine.has_active_candidates
        assert machine.get_current_section() is None
        assert machine.get_current_block_id() is None

    def test_text_content_event_for_regular_line(self, machine: BlockStateMachine) -> None:
        """Regular lines should produce TextContentEvent."""
        events = machine.process_line("Hello world", 1)

        assert len(events) == 1
        assert isinstance(events[0], TextContentEvent)
        assert events[0].content == "Hello world"
        assert events[0].line_number == 1


class TestBlockDetection:
    """Tests for block detection."""

    def test_block_opening_detected(self, machine: BlockStateMachine) -> None:
        """Opening marker should be detected and create candidate."""
        events = machine.process_line("!!test:files_operations", 1)

        assert len(events) == 1
        assert isinstance(events[0], BlockStartEvent)
        assert events[0].start_line == 1
        assert machine.has_active_candidates

    def test_block_id_assigned(self, machine: BlockStateMachine) -> None:
        """Block should get unique ID on opening."""
        events = machine.process_line("!!test:files_operations", 1)

        block_id = events[0].block_id
        assert block_id is not None
        assert machine.get_current_block_id() == block_id

    def test_block_content_accumulates(self, machine: BlockStateMachine) -> None:
        """Content lines should be accumulated."""
        machine.process_line("!!test:files_operations", 1)
        events = machine.process_line("file.py:C", 2)

        # Should emit a delta event
        assert len(events) == 1
        assert events[0].type in (
            EventType.BLOCK_HEADER_DELTA,
            EventType.BLOCK_CONTENT_DELTA,
        )

    def test_block_closing_detected(self, machine: BlockStateMachine) -> None:
        """Closing marker should trigger extraction."""
        machine.process_line("!!test:files_operations", 1)
        machine.process_line("file.py:C", 2)
        events = machine.process_line("!!end", 3)

        # With section end events enabled, we get BlockContentEndEvent + BlockEndEvent
        assert len(events) == 2
        assert isinstance(events[0], BlockContentEndEvent)
        assert isinstance(events[1], BlockEndEvent)
        assert events[1].start_line == 1
        assert events[1].end_line == 3
        assert not machine.has_active_candidates


class TestBlockExtraction:
    """Tests for block extraction."""

    def test_successful_extraction(self, machine: BlockStateMachine) -> None:
        """Valid block should be extracted successfully."""
        machine.process_line("!!test:files_operations", 1)
        machine.process_line("file.py:C", 2)
        events = machine.process_line("!!end", 3)

        # With section end events, we get BlockContentEndEvent + BlockEndEvent
        block_end = next(e for e in events if isinstance(e, BlockEndEvent))
        assert block_end.block_type == "files_operations"
        assert block_end.hash_id is not None
        assert "operations" in block_end.content

    def test_extraction_preserves_block_id(self, machine: BlockStateMachine) -> None:
        """Block ID should be consistent from start to end."""
        start_events = machine.process_line("!!test:files_operations", 1)
        start_block_id = start_events[0].block_id

        machine.process_line("file.py:C", 2)
        end_events = machine.process_line("!!end", 3)

        block_end = next(e for e in end_events if isinstance(e, BlockEndEvent))
        assert block_end.block_id == start_block_id


class TestBlockErrors:
    """Tests for error handling."""

    def test_unclosed_block_on_flush(self, machine: BlockStateMachine) -> None:
        """Unclosed blocks should generate error on flush."""
        machine.process_line("!!test:files_operations", 1)
        machine.process_line("file.py:C", 2)

        events = machine.flush(current_line_number=2)

        assert len(events) == 1
        assert isinstance(events[0], BlockErrorEvent)
        assert events[0].error_code == BlockErrorCode.UNCLOSED_BLOCK
        assert "closing" in events[0].reason.lower()

    def test_size_exceeded_error(self, syntax: DelimiterPreambleSyntax, registry: Registry) -> None:
        """Blocks exceeding size limit should generate error."""
        machine = BlockStateMachine(syntax, registry, max_block_size=50)

        machine.process_line("!!test:files_operations", 1)
        # Add a line that exceeds the size limit
        events = machine.process_line("x" * 100 + ":C", 2)

        # Should contain an error event
        error_events = [e for e in events if isinstance(e, BlockErrorEvent)]
        assert len(error_events) == 1
        assert error_events[0].error_code == BlockErrorCode.SIZE_EXCEEDED


class TestMultipleBlocks:
    """Tests for processing multiple blocks."""

    def test_sequential_blocks(self, machine: BlockStateMachine) -> None:
        """Multiple blocks in sequence should all be extracted."""
        # First block
        machine.process_line("!!block1:files_operations", 1)
        machine.process_line("file1.py:C", 2)
        events1 = machine.process_line("!!end", 3)

        # With section end events: BlockContentEndEvent + BlockEndEvent
        assert len(events1) == 2
        assert any(isinstance(e, BlockEndEvent) for e in events1)

        # Second block
        machine.process_line("!!block2:files_operations", 4)
        machine.process_line("file2.py:E", 5)
        events2 = machine.process_line("!!end", 6)

        assert len(events2) == 2
        assert any(isinstance(e, BlockEndEvent) for e in events2)

    def test_different_block_ids(self, machine: BlockStateMachine) -> None:
        """Each block should get unique ID."""
        machine.process_line("!!block1:files_operations", 1)
        machine.process_line("file1.py:C", 2)
        events1 = machine.process_line("!!end", 3)

        machine.process_line("!!block2:files_operations", 4)
        machine.process_line("file2.py:E", 5)
        events2 = machine.process_line("!!end", 6)

        assert events1[0].block_id != events2[0].block_id


class TestSectionDeltaEvents:
    """Tests for section-specific delta events."""

    def test_header_delta_event(self, machine: BlockStateMachine) -> None:
        """Header section should emit BlockHeaderDeltaEvent."""
        machine.process_line("!!test:files_operations", 1)

        # BlockStartEvent is first, but we should check candidates
        assert machine.has_active_candidates
        assert machine.get_current_section() == "header"

    def test_content_delta_event(self, machine: BlockStateMachine) -> None:
        """Content section should emit BlockContentDeltaEvent."""
        machine.process_line("!!test:files_operations", 1)
        events = machine.process_line("file.py:C", 2)

        # Should have section delta event
        delta_events = [e for e in events if isinstance(e, (BlockHeaderDeltaEvent, BlockContentDeltaEvent))]
        assert len(delta_events) >= 1


class TestReset:
    """Tests for reset functionality."""

    def test_reset_clears_candidates(self, machine: BlockStateMachine) -> None:
        """Reset should clear all candidates."""
        machine.process_line("!!test:files_operations", 1)
        assert machine.has_active_candidates

        machine.reset()

        assert not machine.has_active_candidates
        assert machine.candidates == []

    def test_reset_allows_new_blocks(self, machine: BlockStateMachine) -> None:
        """Reset should allow processing new blocks."""
        machine.process_line("!!old:files_operations", 1)
        machine.reset()

        events = machine.process_line("!!new:files_operations", 1)

        assert len(events) == 1
        assert isinstance(events[0], BlockStartEvent)


class TestFlush:
    """Tests for flush functionality."""

    def test_flush_clears_candidates(self, machine: BlockStateMachine) -> None:
        """Flush should clear all candidates."""
        machine.process_line("!!test:files_operations", 1)
        machine.flush()

        assert not machine.has_active_candidates

    def test_flush_returns_errors_for_all_candidates(self, machine: BlockStateMachine) -> None:
        """Flush should return error for each unclosed block."""
        machine.process_line("!!block1:files_operations", 1)
        # In practice only one block at a time, but test the mechanism
        events = machine.flush(current_line_number=1)

        assert len(events) == 1
        assert all(isinstance(e, BlockErrorEvent) for e in events)

    def test_flush_empty_returns_empty(self, machine: BlockStateMachine) -> None:
        """Flush with no candidates should return empty list."""
        events = machine.flush()
        assert events == []


class TestMetadataValidationModes:
    """Tests for different metadata validation failure modes.

    These tests cover branch 216->233 in block_state_machine.py.
    """

    def test_metadata_validation_failure_continue_mode(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test metadata validation failure with CONTINUE mode.

        When metadata validation fails but mode is CONTINUE, processing should
        continue instead of aborting. This covers branch 216->233.
        """
        from hother.streamblocks.core.block_state_machine import BlockStateMachine
        from hother.streamblocks.core.registry import MetadataValidationFailureMode, ValidationResult
        from hother.streamblocks.syntaxes.delimiter import DelimiterFrontmatterSyntax

        # Use DelimiterFrontmatterSyntax to get proper metadata section handling
        frontmatter_syntax = DelimiterFrontmatterSyntax()

        # Create registry with CONTINUE mode
        registry = Registry(
            syntax=frontmatter_syntax,
            metadata_failure_mode=MetadataValidationFailureMode.CONTINUE,
        )
        registry.register("test", FileOperations)

        # Add a metadata validator that fails
        def failing_metadata_validator(raw: str, parsed: dict | None) -> ValidationResult:
            return ValidationResult.failure("Intentional failure for test")

        registry.add_metadata_validator("test", failing_metadata_validator)

        machine = BlockStateMachine(frontmatter_syntax, registry)

        # Process a block with YAML frontmatter
        machine.process_line("!!start", 1)
        machine.process_line("---", 2)
        machine.process_line("block_type: test", 3)
        machine.process_line("id: test-id", 4)
        events = machine.process_line("---", 5)  # End of metadata, triggers validation

        # With CONTINUE mode, we should NOT get an error event here
        # The block should continue processing
        error_events = [e for e in events if isinstance(e, BlockErrorEvent)]
        assert len(error_events) == 0, "CONTINUE mode should not generate immediate error"

        # Verify we still have an active candidate
        assert machine.has_active_candidates

    def test_metadata_validation_failure_skip_content_mode(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test metadata validation failure with SKIP_CONTENT mode.

        Similar to CONTINUE mode, SKIP_CONTENT should not abort immediately.
        This also covers branch 216->233.
        """
        from hother.streamblocks.core.block_state_machine import BlockStateMachine
        from hother.streamblocks.core.registry import MetadataValidationFailureMode, ValidationResult
        from hother.streamblocks.syntaxes.delimiter import DelimiterFrontmatterSyntax

        frontmatter_syntax = DelimiterFrontmatterSyntax()

        registry = Registry(
            syntax=frontmatter_syntax,
            metadata_failure_mode=MetadataValidationFailureMode.SKIP_CONTENT,
        )
        registry.register("test", FileOperations)

        def failing_metadata_validator(raw: str, parsed: dict | None) -> ValidationResult:
            return ValidationResult.failure("Intentional failure for test")

        registry.add_metadata_validator("test", failing_metadata_validator)

        machine = BlockStateMachine(frontmatter_syntax, registry)

        machine.process_line("!!start", 1)
        machine.process_line("---", 2)
        machine.process_line("block_type: test", 3)
        machine.process_line("id: test-id", 4)
        events = machine.process_line("---", 5)

        # With SKIP_CONTENT mode, we should NOT get an error event here
        error_events = [e for e in events if isinstance(e, BlockErrorEvent)]
        assert len(error_events) == 0, "SKIP_CONTENT mode should not generate immediate error"


class TestParseFailures:
    """Tests for parse failure handling.

    These tests cover lines 379-387, 395-396, 411-416, 422-427 in block_state_machine.py.
    """

    def test_parse_failure_generates_error_event(self, syntax: DelimiterPreambleSyntax, registry: Registry) -> None:
        """Parse failure should generate BlockErrorEvent with PARSE_FAILED code.

        This covers lines 379-387.
        """
        from unittest.mock import patch

        from hother.streamblocks.core.types import ParseResult

        machine = BlockStateMachine(syntax, registry)

        # Start a block
        machine.process_line("!!test:files_operations", 1)
        machine.process_line("file.py:C", 2)

        # Mock the syntax's parse_block to return a failure
        with patch.object(syntax, "parse_block", return_value=ParseResult(success=False, error="Test parse error")):
            events = machine.process_line("!!end", 3)

        # Should have an error event
        error_events = [e for e in events if isinstance(e, BlockErrorEvent)]
        assert len(error_events) >= 1
        assert error_events[0].error_code == BlockErrorCode.PARSE_FAILED
        assert "parse error" in error_events[0].reason.lower() or "parse failed" in error_events[0].reason.lower()

    def test_parse_failure_with_no_error_message(self, syntax: DelimiterPreambleSyntax, registry: Registry) -> None:
        """Parse failure with None error should use default message.

        This covers the fallback to 'Parse failed' on line 379.
        """
        from unittest.mock import patch

        from hother.streamblocks.core.types import ParseResult

        machine = BlockStateMachine(syntax, registry)

        machine.process_line("!!test:files_operations", 1)
        machine.process_line("file.py:C", 2)

        # Mock parse_block to return failure with no error message
        with patch.object(syntax, "parse_block", return_value=ParseResult(success=False, error=None)):
            events = machine.process_line("!!end", 3)

        error_events = [e for e in events if isinstance(e, BlockErrorEvent)]
        assert len(error_events) >= 1
        assert error_events[0].error_code == BlockErrorCode.PARSE_FAILED

    def test_missing_metadata_generates_error(self, syntax: DelimiterPreambleSyntax, registry: Registry) -> None:
        """Missing metadata in parse result should generate error.

        This covers lines 395-396.
        """
        from unittest.mock import MagicMock, patch

        machine = BlockStateMachine(syntax, registry)

        machine.process_line("!!test:files_operations", 1)
        machine.process_line("file.py:C", 2)

        # Create a mock ParseResult that returns None for metadata
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.metadata = None
        mock_result.content = MagicMock()

        with patch.object(syntax, "parse_block", return_value=mock_result):
            events = machine.process_line("!!end", 3)

        error_events = [e for e in events if isinstance(e, BlockErrorEvent)]
        assert len(error_events) >= 1
        assert error_events[0].error_code == BlockErrorCode.MISSING_METADATA

    def test_missing_content_generates_error(self, syntax: DelimiterPreambleSyntax, registry: Registry) -> None:
        """Missing content in parse result should generate error.

        This covers lines 395-396.
        """
        from unittest.mock import MagicMock, patch

        machine = BlockStateMachine(syntax, registry)

        machine.process_line("!!test:files_operations", 1)
        machine.process_line("file.py:C", 2)

        # Create a mock ParseResult that returns None for content
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.metadata = MagicMock()
        mock_result.metadata.block_type = "test"
        mock_result.content = None

        with patch.object(syntax, "parse_block", return_value=mock_result):
            events = machine.process_line("!!end", 3)

        error_events = [e for e in events if isinstance(e, BlockErrorEvent)]
        assert len(error_events) >= 1
        assert error_events[0].error_code == BlockErrorCode.MISSING_CONTENT

    def test_syntax_validation_failure_generates_error(
        self, syntax: DelimiterPreambleSyntax, registry: Registry
    ) -> None:
        """Syntax validation failure should generate error.

        This covers lines 411-416.
        """
        from unittest.mock import patch

        machine = BlockStateMachine(syntax, registry)

        machine.process_line("!!test:files_operations", 1)
        machine.process_line("file.py:C", 2)

        # Mock syntax.validate_block to return False
        with patch.object(syntax, "validate_block", return_value=False):
            events = machine.process_line("!!end", 3)

        error_events = [e for e in events if isinstance(e, BlockErrorEvent)]
        assert len(error_events) >= 1
        assert error_events[0].error_code == BlockErrorCode.VALIDATION_FAILED
        assert "syntax validation" in error_events[0].reason.lower()

    def test_registry_validation_failure_generates_error(
        self, syntax: DelimiterPreambleSyntax, registry: Registry
    ) -> None:
        """Registry validation failure should generate error.

        This covers lines 422-427.
        """
        from unittest.mock import patch

        machine = BlockStateMachine(syntax, registry)

        machine.process_line("!!test:files_operations", 1)
        machine.process_line("file.py:C", 2)

        # Mock registry.validate_block to return False
        with patch.object(registry, "validate_block", return_value=False):
            events = machine.process_line("!!end", 3)

        error_events = [e for e in events if isinstance(e, BlockErrorEvent)]
        assert len(error_events) >= 1
        assert error_events[0].error_code == BlockErrorCode.VALIDATION_FAILED
        assert "registry validation" in error_events[0].reason.lower()
