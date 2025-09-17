# Track 4: Stream Processing Engine (Core)

## Overview
Implement the main stream processing engine that coordinates syntax detection and block extraction.

## TODO List

### StreamBlockProcessor Implementation
- [ ] Create core/processor.py
  - [ ] Import required types and modules
  - [ ] Define StreamBlockProcessor class
    - [ ] Constructor parameters:
      - [ ] registry: BlockRegistry
      - [ ] lines_buffer: int = 5
      - [ ] max_line_length: int = 16_384
      - [ ] max_block_size: int = 1_048_576 (1MB)
    - [ ] Instance variables:
      - [ ] self.registry = registry
      - [ ] self.lines_buffer = lines_buffer
      - [ ] self.max_line_length = max_line_length
      - [ ] self.max_block_size = max_block_size
      - [ ] self._buffer = deque(maxlen=lines_buffer)
      - [ ] self._candidates: list[BlockCandidate] = []
      - [ ] self._line_counter = 0
      - [ ] self._accumulated_text = []

### Core Processing Methods
- [ ] Implement process_stream method
  - [ ] Signature: async def process_stream(stream: AsyncIterator[str]) -> AsyncGenerator[StreamEvent, None]
  - [ ] Main loop: async for chunk in stream
    - [ ] Accumulate chunks in _accumulated_text
    - [ ] Split into complete lines
    - [ ] Handle incomplete lines
    - [ ] Process each complete line
    - [ ] Enforce max_line_length
    - [ ] Increment line counter
    - [ ] Yield events from _process_line
  - [ ] After stream ends: flush remaining candidates

- [ ] Implement _process_line method
  - [ ] Signature: async def _process_line(line: str) -> AsyncGenerator[StreamEvent, None]
  - [ ] Add line to buffer
  - [ ] Check active candidates first
    - [ ] For each candidate:
      - [ ] Call syntax.detect_line(line, candidate)
      - [ ] Handle is_closing
      - [ ] Handle is_metadata_boundary
      - [ ] Handle regular line
      - [ ] Check size limits
      - [ ] Emit BLOCK_DELTA events
  - [ ] If not handled by candidates:
    - [ ] Check for new block openings
    - [ ] Try each syntax in priority order
    - [ ] Create new candidate if opening found
  - [ ] If no match: emit RAW_TEXT event

### Block Extraction Logic
- [ ] Implement _try_extract_block method
  - [ ] Signature: async def _try_extract_block(candidate: BlockCandidate) -> StreamEvent | None
  - [ ] Call syntax.parse_block(candidate)
  - [ ] If parsing fails: return None
  - [ ] Call syntax.validate_block(metadata, content)
  - [ ] Call registry.validate_block (if block_type exists)
  - [ ] Create Block instance
  - [ ] Return BLOCK_EXTRACTED event

- [ ] Implement _create_rejection_event method
  - [ ] Signature: def _create_rejection_event(candidate: BlockCandidate, reason: str = "Validation failed") -> StreamEvent
  - [ ] Create BLOCK_REJECTED event
  - [ ] Include reason, syntax name, line range

- [ ] Implement _flush_candidates method
  - [ ] Signature: async def _flush_candidates() -> AsyncGenerator[StreamEvent, None]
  - [ ] For each remaining candidate:
    - [ ] Create rejection event
    - [ ] Reason: "Stream ended without closing marker"
  - [ ] Clear candidates list

### Event Generation
- [ ] Define event metadata structures
  - [ ] RAW_TEXT metadata: {"line_number": int}
  - [ ] BLOCK_DELTA metadata:
    - [ ] "syntax": str
    - [ ] "start_line": int
    - [ ] "current_line": int
    - [ ] "section": str
    - [ ] "partial_block": {"delta": str, "accumulated": str}
  - [ ] BLOCK_EXTRACTED metadata:
    - [ ] "extracted_block": Block
  - [ ] BLOCK_REJECTED metadata:
    - [ ] "reason": str
    - [ ] "syntax": str
    - [ ] "lines": tuple[int, int]

### Testing Infrastructure
- [ ] Create tests/unit/test_processor.py
  - [ ] Test basic stream processing
    - [ ] Simple text stream
    - [ ] Stream with single block
    - [ ] Stream with multiple blocks
    - [ ] Empty stream
  - [ ] Test event generation
    - [ ] RAW_TEXT events
    - [ ] BLOCK_DELTA events
    - [ ] BLOCK_EXTRACTED events
    - [ ] BLOCK_REJECTED events
  - [ ] Test line handling
    - [ ] Complete lines
    - [ ] Incomplete lines
    - [ ] Very long lines
    - [ ] Empty lines
  - [ ] Test candidate management
    - [ ] Multiple active candidates
    - [ ] Candidate lifecycle
    - [ ] Size limit enforcement

- [ ] Create tests/integration/test_processor_integration.py
  - [ ] Test with all built-in syntaxes
  - [ ] Test interleaved blocks
  - [ ] Test syntax priority
  - [ ] Test error recovery
  - [ ] Test memory usage
  - [ ] Test performance

- [ ] Create test utilities
  - [ ] Mock stream generator
  - [ ] Event collector
  - [ ] Assertion helpers

### Edge Case Handling
- [ ] Test nested block appearance
- [ ] Test immediate contradictions
- [ ] Test buffer boundaries
- [ ] Test very large blocks
- [ ] Test malformed blocks
- [ ] Test concurrent candidates
- [ ] Test stream interruption

### Performance Considerations
- [ ] Profile line processing
- [ ] Profile memory usage
- [ ] Establish baseline metrics
- [ ] Document performance characteristics

### Documentation
- [ ] Document processor lifecycle
- [ ] Document event flow
- [ ] Document candidate states
- [ ] Add usage examples
- [ ] Document configuration options

### Type Checking and Quality
- [ ] Run mypy on processor code
- [ ] Check async type annotations
- [ ] Run ruff linter and formatter
- [ ] Ensure >90% test coverage

## Deliverables
1. Complete StreamBlockProcessor implementation
2. All event types properly generated
3. Robust line and chunk handling
4. Candidate lifecycle management
5. Comprehensive test suite
6. Performance baseline established

## Success Criteria
- [ ] Processes async streams correctly
- [ ] No bytes lost or duplicated
- [ ] All event types emitted appropriately
- [ ] Handles multiple active candidates
- [ ] Enforces size limits
- [ ] Graceful error handling
- [ ] Interleaved blocks work correctly
- [ ] >90% test coverage
- [ ] Performance: >10K lines/second
- [ ] Memory usage stable

## Testing Checklist
- [ ] Unit tests for all processor methods
- [ ] Unit tests for event generation
- [ ] Unit tests for line accumulation
- [ ] Unit tests for candidate management
- [ ] Integration tests with real syntaxes
- [ ] Edge case tests
- [ ] Performance benchmarks
- [ ] Memory leak tests
- [ ] Stress tests with large streams
- [ ] Concurrent processing tests
- [ ] Stream interruption tests
