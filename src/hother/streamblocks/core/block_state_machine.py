"""Block state machine for StreamBlocks."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import uuid4

from hother.streamblocks.core._logger import StdlibLoggerAdapter
from hother.streamblocks.core.models import BlockCandidate, ExtractedBlock
from hother.streamblocks.core.registry import MetadataValidationFailureMode
from hother.streamblocks.core.types import (
    BaseContent,
    BaseMetadata,
    BlockContentDeltaEvent,
    BlockContentEndEvent,
    BlockEndEvent,
    BlockErrorCode,
    BlockErrorEvent,
    BlockHeaderDeltaEvent,
    BlockMetadataDeltaEvent,
    BlockMetadataEndEvent,
    BlockStartEvent,
    BlockState,
    Event,
    ParseResult,
    SectionType,
    TextContentEvent,
)
from hother.streamblocks.core.utils import get_syntax_name

if TYPE_CHECKING:
    from hother.streamblocks.core._logger import Logger
    from hother.streamblocks.core.registry import Registry
    from hother.streamblocks.syntaxes.base import BaseSyntax


class BlockStateMachine:
    """Manages block detection, accumulation, and extraction.

    This class encapsulates the state machine logic for processing blocks:
    - Detecting block openings and closings
    - Accumulating lines into block candidates
    - Extracting and validating complete blocks
    - Generating appropriate events

    Example:
        >>> machine = BlockStateMachine(syntax, registry, max_block_size=1_048_576)
        >>> for line_num, line in lines:
        ...     events = machine.process_line(line, line_num)
        ...     for event in events:
        ...         handle(event)
        >>> final_events = machine.flush()
    """

    def __init__(
        self,
        syntax: BaseSyntax,
        registry: Registry,
        *,
        max_block_size: int = 1_048_576,
        emit_section_end_events: bool = True,
        logger: Logger | None = None,
    ) -> None:
        """Initialize the block state machine.

        Args:
            syntax: The syntax for detecting and parsing blocks
            registry: Registry for block class lookup and validation
            max_block_size: Maximum block size in bytes before rejection
            emit_section_end_events: Whether to emit BlockMetadataEndEvent and
                BlockContentEndEvent when sections complete. Default True.
            logger: Optional logger for debug output
        """
        self._syntax = syntax
        self._registry = registry
        self._max_block_size = max_block_size
        self._emit_section_end_events = emit_section_end_events
        self._logger = logger or StdlibLoggerAdapter(logging.getLogger(__name__))

        # State
        self._candidates: list[BlockCandidate] = []
        self._block_ids: dict[int, str] = {}  # Maps start_line to block_id

    @property
    def candidates(self) -> list[BlockCandidate]:
        """Get the list of active block candidates."""
        return list(self._candidates)

    @property
    def has_active_candidates(self) -> bool:
        """Check if there are active block candidates."""
        return len(self._candidates) > 0

    def get_block_id(self, candidate_start_line: int) -> str:
        """Get or create a block_id for a candidate."""
        if candidate_start_line not in self._block_ids:
            self._block_ids[candidate_start_line] = str(uuid4())
        return self._block_ids[candidate_start_line]

    def get_current_section(self) -> str | None:
        """Get the current section of the first active candidate."""
        if self._candidates:
            return self._candidates[0].current_section
        return None

    def get_current_block_id(self) -> str | None:
        """Get the block_id of the first active candidate."""
        if self._candidates:
            return self.get_block_id(self._candidates[0].start_line)
        return None

    def process_line(self, line: str, line_number: int) -> list[Event]:
        """Process a single line through the block detection state machine.

        Args:
            line: Line content to process
            line_number: Line number (1-indexed)

        Returns:
            List of events generated from processing this line
        """
        events: list[Event] = []

        # 1. Handle active candidates
        handled, candidate_events = self._process_active_candidates(line, line_number)
        events.extend(candidate_events)

        # 2. Check for new blocks if not handled
        if not handled:
            new_block_events = self._check_new_blocks(line, line_number)
            events.extend(new_block_events)

        return events

    def _process_active_candidates(self, line: str, line_number: int) -> tuple[bool, list[Event]]:
        """Process line against all active candidates.

        Returns:
            Tuple of (handled, events)
        """
        events: list[Event] = []
        handled = False

        for candidate in list(self._candidates):
            # Capture section BEFORE detect_line (which may modify it)
            old_section = candidate.current_section

            # Let the syntax check this line in context
            detection = candidate.syntax.detect_line(line, candidate)

            if detection.is_closing:
                events.extend(self._handle_closing(candidate, line, line_number))
                handled = True
            elif detection.is_metadata_boundary:
                events.extend(self._handle_boundary(candidate, line, line_number, old_section))
                handled = True
            else:
                events.extend(self._handle_content(candidate, line, line_number))
                handled = True

        return handled, events

    def _handle_closing(self, candidate: BlockCandidate, line: str, line_number: int) -> list[Event]:
        """Handle block closing detection."""
        events: list[Event] = []

        # Found closing marker
        candidate.add_line(line)
        candidate.state = BlockState.CLOSING_DETECTED

        # Emit BlockContentEndEvent before extraction (if enabled)
        if self._emit_section_end_events:
            content_end_event = self._create_content_end_event(candidate, line_number)
            events.append(content_end_event)

            # Handle content validation failure
            if not content_end_event.validation_passed:
                error_msg = content_end_event.validation_error or "Content validation failed"
                events.append(
                    self._create_error_event(
                        candidate,
                        line_number,
                        error_msg,
                        BlockErrorCode.VALIDATION_FAILED,
                    )
                )
                self._candidates.remove(candidate)
                return events

        # Try to extract block
        event = self._try_extract_block(candidate, line_number)
        events.append(event)
        self._candidates.remove(candidate)
        return events

    def _handle_boundary(self, candidate: BlockCandidate, line: str, line_number: int, old_section: str) -> list[Event]:
        """Handle metadata boundary detection."""
        events: list[Event] = []

        # Syntax detected a metadata boundary
        candidate.add_line(line)

        # Emit section-specific delta event with boundary flag
        events.append(self._create_section_delta_event(candidate, line, line_number, is_boundary=True))

        # Check if metadata section just ended (transition to content)
        if (
            self._emit_section_end_events
            and old_section == SectionType.METADATA
            and candidate.current_section == SectionType.CONTENT
        ):
            metadata_end_event = self._create_metadata_end_event(candidate, line_number)
            events.append(metadata_end_event)

            # Handle metadata validation failure
            if not metadata_end_event.validation_passed:
                failure_mode = self._registry.metadata_failure_mode

                if failure_mode == MetadataValidationFailureMode.ABORT_BLOCK:
                    # Abort the block immediately
                    error_msg = metadata_end_event.validation_error or "Metadata validation failed"
                    events.append(
                        self._create_error_event(
                            candidate,
                            line_number,
                            error_msg,
                            BlockErrorCode.VALIDATION_FAILED,
                        )
                    )
                    self._candidates.remove(candidate)
                    return events

                # CONTINUE and SKIP_CONTENT modes - continue processing
                # (actual handling at block end)

        return events

    def _handle_content(self, candidate: BlockCandidate, line: str, line_number: int) -> list[Event]:
        """Handle regular content line."""
        events: list[Event] = []

        # Regular line inside block
        candidate.add_line(line)

        # Check size limit
        if len(candidate.raw_text) > self._max_block_size:
            events.append(
                self._create_error_event(
                    candidate,
                    line_number,
                    "Block size exceeded",
                    BlockErrorCode.SIZE_EXCEEDED,
                )
            )
            self._candidates.remove(candidate)
            return events

        # Emit section-specific delta event
        events.append(self._create_section_delta_event(candidate, line, line_number))
        return events

    def _check_new_blocks(self, line: str, line_number: int) -> list[Event]:
        """Check if line starts a new block."""
        events: list[Event] = []
        opening_found = False

        # Check if this line opens a new block
        detection = self._syntax.detect_line(line, None)

        if detection.is_opening:
            # Start new candidate
            candidate = BlockCandidate(self._syntax, line_number)
            candidate.add_line(line)

            # If syntax provided inline metadata, store it
            if detection.metadata:
                candidate.metadata_lines = [str(detection.metadata)]

            self._candidates.append(candidate)
            opening_found = True

            # Emit BlockStartEvent
            block_id = self.get_block_id(candidate.start_line)
            events.append(
                BlockStartEvent(
                    block_id=block_id,
                    block_type=None,  # Not known until parsed
                    syntax=get_syntax_name(candidate.syntax),
                    start_line=candidate.start_line,
                    inline_metadata=detection.metadata,
                )
            )

            self._logger.debug(
                "block_candidate_created",
                syntax=get_syntax_name(candidate.syntax),
                start_line=candidate.start_line,
                inline_metadata=bool(detection.metadata),
            )

        # If no candidates and no openings, emit text content
        if not opening_found:
            events.append(
                TextContentEvent(
                    content=line,
                    line_number=line_number,
                )
            )

        return events

    def flush(self, current_line_number: int | None = None) -> list[Event]:
        """Flush remaining candidates as errors.

        Call this at stream end to generate error events for any
        blocks that were opened but never closed.

        Args:
            current_line_number: Current line number for error events

        Returns:
            List of error events for remaining candidates
        """
        events: list[Event] = []
        line_num = current_line_number or 0

        for candidate in self._candidates:
            # Use last known line number from candidate if available
            end_line = line_num if line_num > 0 else candidate.start_line + len(candidate.lines)
            events.append(
                self._create_error_event(
                    candidate,
                    end_line,
                    "Stream ended without closing marker",
                    BlockErrorCode.UNCLOSED_BLOCK,
                )
            )

        self._candidates.clear()
        return events

    def reset(self) -> None:
        """Reset the state machine."""
        self._candidates.clear()
        self._block_ids.clear()

    def _parse_candidate(self, candidate: BlockCandidate) -> tuple[str | None, ParseResult[BaseMetadata, BaseContent]]:
        """Extract block type, look up class, and parse the candidate.

        Args:
            candidate: Block candidate to parse

        Returns:
            Tuple of (block_type, parse_result)
        """
        # Extract block_type from candidate
        block_type = candidate.syntax.extract_block_type(candidate)

        # Look up block_class from registry
        block_class = self._registry.get_block_class(block_type) if block_type else None

        # Parse with the appropriate block_class
        parse_result = candidate.syntax.parse_block(candidate, block_class)

        return block_type, parse_result

    def _create_extracted_block(
        self,
        candidate: BlockCandidate,
        parse_result: ParseResult[BaseMetadata, BaseContent],
        line_number: int,
    ) -> ExtractedBlock[BaseMetadata, BaseContent]:
        """Create ExtractedBlock from parse result.

        Args:
            candidate: Block candidate
            parse_result: Successful parse result
            line_number: Current line number (end of block)

        Returns:
            ExtractedBlock with metadata, content, and extraction info
        """
        return ExtractedBlock(
            metadata=parse_result.metadata,  # type: ignore[arg-type]  # Checked by caller
            content=parse_result.content,  # type: ignore[arg-type]  # Checked by caller
            syntax_name=get_syntax_name(candidate.syntax),
            raw_text=candidate.raw_text,
            line_start=candidate.start_line,
            line_end=line_number,
            hash_id=candidate.compute_hash(),
        )

    def _validate_extracted_block(
        self,
        candidate: BlockCandidate,
        block: ExtractedBlock[BaseMetadata, BaseContent],
        block_type: str | None,
        line_number: int,
    ) -> BlockErrorEvent | None:
        """Run syntax and registry validation on extracted block.

        Args:
            candidate: Block candidate
            block: Extracted block to validate
            block_type: Block type from candidate
            line_number: Current line number

        Returns:
            BlockErrorEvent if validation fails, None if passes
        """
        # Syntax validation
        if not candidate.syntax.validate_block(block):
            self._logger.warning(
                "syntax_validation_failed",
                block_type=block_type,
                syntax=block.syntax_name,
            )
            return self._create_error_event(
                candidate, line_number, "Syntax validation failed", BlockErrorCode.VALIDATION_FAILED
            )

        # Registry validation (user-defined validators)
        if not self._registry.validate_block(block):
            self._logger.warning(
                "registry_validation_failed",
                block_type=block_type,
                syntax=block.syntax_name,
            )
            return self._create_error_event(
                candidate, line_number, "Registry validation failed", BlockErrorCode.VALIDATION_FAILED
            )

        return None

    def _create_success_event(
        self,
        candidate: BlockCandidate,
        block: ExtractedBlock[BaseMetadata, BaseContent],
        block_type: str | None,
    ) -> BlockEndEvent:
        """Create BlockEndEvent for successful extraction.

        Args:
            candidate: Block candidate
            block: Successfully extracted and validated block
            block_type: Block type from candidate

        Returns:
            BlockEndEvent with all block information
        """
        self._logger.info(
            "block_extracted",
            block_type=block_type,
            block_id=block.hash_id,
            syntax=block.syntax_name,
            lines=(block.line_start, block.line_end),
            size_bytes=len(block.raw_text),
        )

        block_id = self.get_block_id(candidate.start_line)

        event = BlockEndEvent(
            block_id=block_id,
            block_type=block_type or block.metadata.block_type,
            syntax=block.syntax_name,
            start_line=block.line_start,
            end_line=block.line_end,
            metadata=block.metadata.model_dump(),
            content=block.content.model_dump(),
            raw_content=block.raw_text,
            hash_id=block.hash_id,
        )
        # Set private attribute after construction
        object.__setattr__(event, "_block", block)
        return event

    def _try_extract_block(
        self,
        candidate: BlockCandidate,
        line_number: int,
    ) -> BlockEndEvent | BlockErrorEvent:
        """Try to parse and validate a complete block.

        This orchestrates the extraction process by delegating to specialized helpers.

        Args:
            candidate: Block candidate to extract
            line_number: Current line number (end of block)

        Returns:
            BlockEndEvent if successful, BlockErrorEvent if validation fails
        """
        # Step 1: Parse the candidate
        block_type, parse_result = self._parse_candidate(candidate)

        self._logger.debug(
            "extracting_block",
            syntax=get_syntax_name(candidate.syntax),
            block_type=block_type,
            start_line=candidate.start_line,
            end_line=line_number,
            size_bytes=len(candidate.raw_text),
        )

        # Handle parse failure
        if not parse_result.success:
            error = parse_result.error or "Parse failed"
            self._logger.warning(
                "block_parse_failed",
                block_type=block_type,
                error=error,
                syntax=get_syntax_name(candidate.syntax),
                exc_info=parse_result.exception,
            )
            return self._create_error_event(
                candidate, line_number, error, BlockErrorCode.PARSE_FAILED, parse_result.exception
            )

        # Check for missing metadata or content
        if parse_result.metadata is None or parse_result.content is None:
            error_code = (
                BlockErrorCode.MISSING_METADATA if parse_result.metadata is None else BlockErrorCode.MISSING_CONTENT
            )
            return self._create_error_event(candidate, line_number, "Missing metadata or content", error_code)

        # Step 2: Create extracted block
        block = self._create_extracted_block(candidate, parse_result, line_number)

        # Step 3: Validate
        validation_error = self._validate_extracted_block(candidate, block, block_type, line_number)
        if validation_error:
            return validation_error

        # Step 4: Success!
        return self._create_success_event(candidate, block, block_type)

    def _create_section_delta_event(
        self,
        candidate: BlockCandidate,
        line: str,
        line_number: int,
        *,
        is_boundary: bool = False,
    ) -> BlockHeaderDeltaEvent | BlockMetadataDeltaEvent | BlockContentDeltaEvent:
        """Create a section-specific delta event based on current section.

        Args:
            candidate: Current block candidate
            line: Line content (delta)
            line_number: Current line number
            is_boundary: Whether this line is a section boundary marker

        Returns:
            Section-specific delta event
        """
        block_id = self.get_block_id(candidate.start_line)
        section = candidate.current_section or SectionType.CONTENT
        syntax_name = get_syntax_name(candidate.syntax)
        accumulated_size = len(candidate.raw_text)

        if section == SectionType.HEADER:
            return BlockHeaderDeltaEvent(
                block_id=block_id,
                delta=line,
                syntax=syntax_name,
                current_line=line_number,
                accumulated_size=accumulated_size,
                inline_metadata=None,
            )
        if section == SectionType.METADATA:
            return BlockMetadataDeltaEvent(
                block_id=block_id,
                delta=line,
                syntax=syntax_name,
                current_line=line_number,
                accumulated_size=accumulated_size,
                is_boundary=is_boundary,
            )
        # Default to content
        return BlockContentDeltaEvent(
            block_id=block_id,
            delta=line,
            syntax=syntax_name,
            current_line=line_number,
            accumulated_size=accumulated_size,
        )

    def _create_error_event(
        self,
        candidate: BlockCandidate,
        line_number: int,
        reason: str = "Validation failed",
        error_code: BlockErrorCode | None = None,
        exception: Exception | None = None,
    ) -> BlockErrorEvent:
        """Create an error event.

        Args:
            candidate: Failed candidate
            line_number: Current line number
            reason: Reason for failure
            error_code: Structured error code
            exception: Optional exception that caused failure

        Returns:
            BlockErrorEvent
        """
        self._logger.warning(
            "block_error",
            reason=reason,
            error_code=error_code,
            syntax=get_syntax_name(candidate.syntax),
            lines=(candidate.start_line, line_number),
            has_exception=exception is not None,
            exc_info=exception if exception else None,
        )

        block_id = self.get_block_id(candidate.start_line)

        return BlockErrorEvent(
            block_id=block_id,
            reason=reason,
            error_code=error_code,
            syntax=get_syntax_name(candidate.syntax),
            start_line=candidate.start_line,
            end_line=line_number,
            exception=exception,
        )

    def _create_metadata_end_event(
        self,
        candidate: BlockCandidate,
        line_number: int,
    ) -> BlockMetadataEndEvent:
        """Create a metadata section end event.

        Performs early metadata parsing and validation.

        Args:
            candidate: Block candidate with metadata accumulated
            line_number: Current line number (end of metadata section)

        Returns:
            BlockMetadataEndEvent with parsed metadata and validation result
        """
        block_id = self.get_block_id(candidate.start_line)
        syntax_name = get_syntax_name(candidate.syntax)

        # Get raw metadata
        raw_metadata = "\n".join(candidate.metadata_lines)

        # Try early parsing
        parsed_metadata = candidate.syntax.parse_metadata_early(candidate)
        candidate.parsed_metadata = parsed_metadata  # Cache for later

        # Run validation if we have parsed metadata
        validation_passed = True
        validation_error: str | None = None

        if parsed_metadata:
            block_type = parsed_metadata.get("block_type")
            if block_type:
                result = self._registry.validate_metadata(block_type, raw_metadata, parsed_metadata)
                validation_passed = result.passed
                validation_error = result.error

                # Cache validation state in candidate
                candidate.cache_metadata_validation(validation_passed, validation_error)

        return BlockMetadataEndEvent(
            block_id=block_id,
            syntax=syntax_name,
            start_line=candidate.start_line,
            end_line=line_number,
            raw_metadata=raw_metadata,
            parsed_metadata=parsed_metadata,
            validation_passed=validation_passed,
            validation_error=validation_error,
        )

    def _create_content_end_event(
        self,
        candidate: BlockCandidate,
        line_number: int,
    ) -> BlockContentEndEvent:
        """Create a content section end event.

        Performs early content parsing and validation.

        Args:
            candidate: Block candidate with content accumulated
            line_number: Current line number (end of content section)

        Returns:
            BlockContentEndEvent with parsed content and validation result
        """
        block_id = self.get_block_id(candidate.start_line)
        syntax_name = get_syntax_name(candidate.syntax)

        # Get raw content
        raw_content = "\n".join(candidate.content_lines)

        # Try early parsing
        parsed_content = candidate.syntax.parse_content_early(candidate)
        candidate.parsed_content = parsed_content  # Cache for later

        # Run validation if we have parsed content
        validation_passed = True
        validation_error: str | None = None

        # Get block_type from parsed metadata or extract from syntax
        block_type = None
        if candidate.parsed_metadata:
            block_type = candidate.parsed_metadata.get("block_type")
        if not block_type:
            # Fall back to extracting from syntax (for preamble syntax which has inline metadata)
            block_type = candidate.syntax.extract_block_type(candidate)

        if block_type and parsed_content:
            result = self._registry.validate_content(block_type, raw_content, parsed_content)
            validation_passed = result.passed
            validation_error = result.error

            # Cache validation state in candidate
            candidate.cache_content_validation(validation_passed, validation_error)

        return BlockContentEndEvent(
            block_id=block_id,
            syntax=syntax_name,
            start_line=candidate.start_line,
            end_line=line_number,
            raw_content=raw_content,
            parsed_content=parsed_content,
            validation_passed=validation_passed,
            validation_error=validation_error,
        )
