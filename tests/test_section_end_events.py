"""Tests for section end events (BlockMetadataEndEvent, BlockContentEndEvent)."""

import pytest

from hother.streamblocks import (
    BlockContentEndEvent,
    BlockEndEvent,
    BlockErrorCode,
    BlockErrorEvent,
    BlockMetadataEndEvent,
    DelimiterFrontmatterSyntax,
    DelimiterPreambleSyntax,
    MetadataValidationFailureMode,
    Registry,
    ValidationResult,
)
from hother.streamblocks.core.block_state_machine import BlockStateMachine
from hother.streamblocks_examples.blocks.agent import FileOperations


@pytest.fixture
def preamble_syntax() -> DelimiterPreambleSyntax:
    """Create a DelimiterPreambleSyntax instance."""
    return DelimiterPreambleSyntax()


@pytest.fixture
def frontmatter_syntax() -> DelimiterFrontmatterSyntax:
    """Create a DelimiterFrontmatterSyntax instance."""
    return DelimiterFrontmatterSyntax()


@pytest.fixture
def registry(preamble_syntax: DelimiterPreambleSyntax) -> Registry:
    """Create registry with preamble syntax."""
    reg = Registry(syntax=preamble_syntax)
    reg.register("files_operations", FileOperations)
    return reg


@pytest.fixture
def frontmatter_registry(frontmatter_syntax: DelimiterFrontmatterSyntax) -> Registry:
    """Create registry with frontmatter syntax."""
    reg = Registry(syntax=frontmatter_syntax)
    reg.register("files_operations", FileOperations)
    return reg


@pytest.fixture
def machine(preamble_syntax: DelimiterPreambleSyntax, registry: Registry) -> BlockStateMachine:
    """Create a BlockStateMachine with section end events enabled."""
    return BlockStateMachine(
        preamble_syntax,
        registry,
        emit_section_end_events=True,
    )


@pytest.fixture
def machine_disabled(preamble_syntax: DelimiterPreambleSyntax, registry: Registry) -> BlockStateMachine:
    """Create a BlockStateMachine with section end events disabled."""
    return BlockStateMachine(
        preamble_syntax,
        registry,
        emit_section_end_events=False,
    )


class TestBlockContentEndEvent:
    """Tests for BlockContentEndEvent emission."""

    def test_content_end_emitted_before_block_end(self, machine: BlockStateMachine) -> None:
        """BlockContentEndEvent should be emitted before BlockEndEvent."""
        machine.process_line("!!test:files_operations", 1)
        machine.process_line("file.py:C", 2)
        events = machine.process_line("!!end", 3)

        assert len(events) == 2
        assert isinstance(events[0], BlockContentEndEvent)
        assert isinstance(events[1], BlockEndEvent)

    def test_content_end_contains_raw_content(self, machine: BlockStateMachine) -> None:
        """BlockContentEndEvent should contain raw content."""
        machine.process_line("!!test:files_operations", 1)
        machine.process_line("file.py:C", 2)
        events = machine.process_line("!!end", 3)

        content_end = events[0]
        assert isinstance(content_end, BlockContentEndEvent)
        # For preamble syntax, content_lines are accumulated differently
        assert content_end.block_id is not None
        assert content_end.syntax == "DelimiterPreambleSyntax"

    def test_content_end_contains_parsed_content(self, machine: BlockStateMachine) -> None:
        """BlockContentEndEvent should contain parsed content when available."""
        machine.process_line("!!test:files_operations", 1)
        machine.process_line("file.py:C", 2)
        events = machine.process_line("!!end", 3)

        content_end = events[0]
        assert isinstance(content_end, BlockContentEndEvent)
        assert content_end.parsed_content is not None
        assert "raw_content" in content_end.parsed_content

    def test_content_end_has_validation_state(self, machine: BlockStateMachine) -> None:
        """BlockContentEndEvent should have validation state."""
        machine.process_line("!!test:files_operations", 1)
        machine.process_line("file.py:C", 2)
        events = machine.process_line("!!end", 3)

        content_end = events[0]
        assert isinstance(content_end, BlockContentEndEvent)
        assert content_end.validation_passed is True
        assert content_end.validation_error is None


class TestSectionEndEventsDisabled:
    """Tests for opt-out behavior."""

    def test_no_content_end_when_disabled(self, machine_disabled: BlockStateMachine) -> None:
        """No section end events when emit_section_end_events=False."""
        machine_disabled.process_line("!!test:files_operations", 1)
        machine_disabled.process_line("file.py:C", 2)
        events = machine_disabled.process_line("!!end", 3)

        # Should only have BlockEndEvent, no BlockContentEndEvent
        assert len(events) == 1
        assert isinstance(events[0], BlockEndEvent)


class TestBlockMetadataEndEvent:
    """Tests for BlockMetadataEndEvent emission with frontmatter syntax."""

    def test_metadata_end_emitted_after_frontmatter(
        self, frontmatter_syntax: DelimiterFrontmatterSyntax, frontmatter_registry: Registry
    ) -> None:
        """BlockMetadataEndEvent should be emitted when metadata section ends."""
        machine = BlockStateMachine(
            frontmatter_syntax,
            frontmatter_registry,
            emit_section_end_events=True,
        )

        machine.process_line("!!start", 1)
        machine.process_line("---", 2)
        machine.process_line("id: test_block", 3)
        machine.process_line("block_type: files_operations", 4)
        # Closing frontmatter triggers metadata end
        events = machine.process_line("---", 5)

        # Should contain BlockMetadataEndEvent
        metadata_end_events = [e for e in events if isinstance(e, BlockMetadataEndEvent)]
        assert len(metadata_end_events) == 1

        metadata_end = metadata_end_events[0]
        assert metadata_end.validation_passed is True
        assert "id: test_block" in metadata_end.raw_metadata
        assert metadata_end.parsed_metadata is not None
        assert metadata_end.parsed_metadata.get("id") == "test_block"


class TestValidationHooks:
    """Tests for early validation hooks."""

    def test_metadata_validation_success(self, frontmatter_syntax: DelimiterFrontmatterSyntax) -> None:
        """Successful metadata validation should pass through."""
        registry = Registry(syntax=frontmatter_syntax)
        registry.register("files_operations", FileOperations)

        def validate_metadata(raw: str, parsed: dict | None) -> ValidationResult:
            if parsed and parsed.get("id"):
                return ValidationResult.success()
            return ValidationResult.failure("Missing id")

        registry.add_metadata_validator("files_operations", validate_metadata)

        machine = BlockStateMachine(
            frontmatter_syntax,
            registry,
            emit_section_end_events=True,
        )

        machine.process_line("!!start", 1)
        machine.process_line("---", 2)
        machine.process_line("id: test", 3)
        machine.process_line("block_type: files_operations", 4)
        events = machine.process_line("---", 5)

        metadata_end = next(e for e in events if isinstance(e, BlockMetadataEndEvent))
        assert metadata_end.validation_passed is True

    def test_metadata_validation_failure_abort(self, frontmatter_syntax: DelimiterFrontmatterSyntax) -> None:
        """Failed metadata validation with ABORT_BLOCK should emit error."""
        registry = Registry(
            syntax=frontmatter_syntax,
            metadata_failure_mode=MetadataValidationFailureMode.ABORT_BLOCK,
        )
        registry.register("files_operations", FileOperations)

        def validate_metadata(raw: str, parsed: dict | None) -> ValidationResult:
            return ValidationResult.failure("Invalid metadata")

        registry.add_metadata_validator("files_operations", validate_metadata)

        machine = BlockStateMachine(
            frontmatter_syntax,
            registry,
            emit_section_end_events=True,
        )

        machine.process_line("!!start", 1)
        machine.process_line("---", 2)
        machine.process_line("id: test", 3)
        machine.process_line("block_type: files_operations", 4)
        events = machine.process_line("---", 5)

        # Should have metadata end event (with failure) and error event
        metadata_end = next(e for e in events if isinstance(e, BlockMetadataEndEvent))
        assert metadata_end.validation_passed is False
        assert metadata_end.validation_error == "Invalid metadata"

        error_events = [e for e in events if isinstance(e, BlockErrorEvent)]
        assert len(error_events) == 1
        assert error_events[0].error_code == BlockErrorCode.VALIDATION_FAILED

    def test_content_validation_failure(self, preamble_syntax: DelimiterPreambleSyntax) -> None:
        """Failed content validation should emit error."""
        registry = Registry(syntax=preamble_syntax)
        registry.register("files_operations", FileOperations)

        def validate_content(raw: str, parsed: dict | None) -> ValidationResult:
            return ValidationResult.failure("Invalid content")

        registry.add_content_validator("files_operations", validate_content)

        machine = BlockStateMachine(
            preamble_syntax,
            registry,
            emit_section_end_events=True,
        )

        machine.process_line("!!test:files_operations", 1)
        machine.process_line("file.py:C", 2)
        events = machine.process_line("!!end", 3)

        # Should have content end event (with failure) and error event
        content_end = next(e for e in events if isinstance(e, BlockContentEndEvent))
        assert content_end.validation_passed is False
        assert content_end.validation_error == "Invalid content"

        error_events = [e for e in events if isinstance(e, BlockErrorEvent)]
        assert len(error_events) == 1


class TestEventSequence:
    """Tests for correct event ordering."""

    def test_event_order_preamble_syntax(self, machine: BlockStateMachine) -> None:
        """Events should be in correct order for preamble syntax."""
        all_events = []

        # Opening
        events = machine.process_line("!!test:files_operations", 1)
        all_events.extend(events)

        # Content
        events = machine.process_line("file.py:C", 2)
        all_events.extend(events)

        # Closing
        events = machine.process_line("!!end", 3)
        all_events.extend(events)

        # Extract event types in order
        event_types = [type(e).__name__ for e in all_events]

        # Should see: BlockStartEvent -> delta events -> BlockContentEndEvent -> BlockEndEvent
        assert "BlockStartEvent" in event_types
        assert "BlockContentEndEvent" in event_types
        assert "BlockEndEvent" in event_types

        # Content end should come before block end
        content_end_idx = event_types.index("BlockContentEndEvent")
        block_end_idx = event_types.index("BlockEndEvent")
        assert content_end_idx < block_end_idx

    def test_event_order_frontmatter_syntax(
        self, frontmatter_syntax: DelimiterFrontmatterSyntax, frontmatter_registry: Registry
    ) -> None:
        """Events should be in correct order for frontmatter syntax."""
        machine = BlockStateMachine(
            frontmatter_syntax,
            frontmatter_registry,
            emit_section_end_events=True,
        )

        all_events = []

        # Opening
        events = machine.process_line("!!start", 1)
        all_events.extend(events)

        # Frontmatter start
        events = machine.process_line("---", 2)
        all_events.extend(events)

        # Metadata
        events = machine.process_line("id: test", 3)
        all_events.extend(events)

        events = machine.process_line("block_type: files_operations", 4)
        all_events.extend(events)

        # Frontmatter end (metadata end event)
        events = machine.process_line("---", 5)
        all_events.extend(events)

        # Content
        events = machine.process_line("file.py:C", 6)
        all_events.extend(events)

        # Closing
        events = machine.process_line("!!end", 7)
        all_events.extend(events)

        event_types = [type(e).__name__ for e in all_events]

        # Should see: BlockStartEvent -> deltas -> BlockMetadataEndEvent -> deltas -> BlockContentEndEvent -> BlockEndEvent
        assert "BlockStartEvent" in event_types
        assert "BlockMetadataEndEvent" in event_types
        assert "BlockContentEndEvent" in event_types
        assert "BlockEndEvent" in event_types

        # Verify order
        metadata_end_idx = event_types.index("BlockMetadataEndEvent")
        content_end_idx = event_types.index("BlockContentEndEvent")
        block_end_idx = event_types.index("BlockEndEvent")

        assert metadata_end_idx < content_end_idx < block_end_idx
