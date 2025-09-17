# Track 6: Error Handling and Recovery

## Overview
Implement comprehensive error handling strategies and malformed block recovery.

## TODO List

### Error Recovery Strategy
- [ ] Create core/errors.py
  - [ ] Define ErrorRecoveryStrategy enum
    - [ ] STRICT = "strict" (reject on any error)
    - [ ] PERMISSIVE = "permissive" (try to extract what we can)
    - [ ] SKIP = "skip" (skip malformed blocks silently)
  - [ ] Define custom exceptions
    - [ ] BlockParsingError
    - [ ] MetadataValidationError
    - [ ] ContentValidationError
    - [ ] SizeLimitExceededError
    - [ ] StreamProcessingError

### RobustStreamProcessor Implementation
- [ ] Create core/robust.py
  - [ ] Import StreamBlockProcessor and error types
  - [ ] Define RobustStreamProcessor(StreamBlockProcessor)
    - [ ] Constructor parameters:
      - [ ] Add error_strategy: ErrorRecoveryStrategy = STRICT
      - [ ] Add max_error_context: int = 100
      - [ ] Add error_callback: Callable | None = None
    - [ ] Instance variables:
      - [ ] self.error_strategy = error_strategy
      - [ ] self._error_log: list[ErrorEntry] = []
      - [ ] self._recovery_stats = RecoveryStats()

### Enhanced Error Handling
- [ ] Override _try_extract_block method
  - [ ] STRICT mode:
    - [ ] Use base implementation
    - [ ] Any error causes rejection
  - [ ] PERMISSIVE mode:
    - [ ] Try normal extraction first
    - [ ] On failure, attempt partial extraction
    - [ ] Try to salvage metadata even if content fails
    - [ ] Try to salvage content even if metadata fails
    - [ ] Create partial block with available data
    - [ ] Add error details to event metadata
  - [ ] SKIP mode:
    - [ ] Silently return None on any error
    - [ ] Log error for debugging

- [ ] Implement _attempt_partial_extraction method
  - [ ] Try different parsing strategies
  - [ ] Fallback to raw content
  - [ ] Create placeholder metadata/content
  - [ ] Document what was recovered

- [ ] Implement _create_empty_content method
  - [ ] Return minimal valid content model
  - [ ] Include error information
  - [ ] Maintain type safety

### Edge Case Handlers
- [ ] Implement handlers for documented edge cases:
  - [ ] Nested blocks (not supported)
    - [ ] Detect and reject with clear message
    - [ ] Include both block positions
  - [ ] Unclosed blocks at EOF
    - [ ] Create specific rejection event
    - [ ] Include partial content in error
  - [ ] Empty blocks
    - [ ] Check if content model allows empty
    - [ ] Handle based on strategy
  - [ ] Malformed metadata
    - [ ] YAML parsing errors
    - [ ] Type validation errors
    - [ ] Missing required fields
  - [ ] Very long lines
    - [ ] Implement progressive truncation
    - [ ] Warn about truncation
  - [ ] Conflicting syntaxes
    - [ ] Document which syntax won
    - [ ] Why others were rejected
  - [ ] Size limit violations
    - [ ] Implement graceful handling
    - [ ] Partial content extraction

### Error Reporting
- [ ] Create comprehensive error events
  - [ ] Enhanced BLOCK_REJECTED metadata:
    - [ ] "error_type": str
    - [ ] "error_message": str
    - [ ] "error_context": dict
    - [ ] "partial_metadata": dict | None
    - [ ] "partial_content": str | None
    - [ ] "recovery_attempted": bool
    - [ ] "line_context": list[str]

- [ ] Implement error context extraction
  - [ ] Show lines around error
  - [ ] Highlight problematic section
  - [ ] Include parser state
  - [ ] Add suggestions for fixes

### Recovery Statistics
- [ ] Track recovery metrics
  - [ ] Blocks successfully recovered
  - [ ] Partial extractions
  - [ ] Types of errors encountered
  - [ ] Recovery success rate
  - [ ] Performance impact

### Testing Suite
- [ ] Create tests/unit/test_error_handling.py
  - [ ] Test each error recovery strategy
  - [ ] Test partial extraction
  - [ ] Test error reporting
  - [ ] Test edge cases

- [ ] Create tests/unit/test_edge_cases.py
  - [ ] Test all documented edge cases:
    - [ ] Nested blocks
    - [ ] Unclosed blocks
    - [ ] Empty blocks
    - [ ] Malformed metadata
    - [ ] Buffer boundaries
    - [ ] Very long lines
    - [ ] Conflicting syntaxes
    - [ ] Immediate contradictions
    - [ ] Interleaved streams

- [ ] Create tests/fuzz/test_fuzzing.py
  - [ ] Random input generation
  - [ ] Mutation testing
  - [ ] Crash detection
  - [ ] Memory safety
  - [ ] Performance under errors

### Error Recovery Examples
- [ ] Create examples/error_handling.py
  - [ ] Show all strategies in action
  - [ ] Demonstrate partial recovery
  - [ ] Show error reporting
  - [ ] Best practices

### Documentation
- [ ] Document error handling strategies
- [ ] Document edge case behaviors
- [ ] Create troubleshooting guide
- [ ] Document recovery limitations
- [ ] Add error handling examples

## Deliverables
1. ErrorRecoveryStrategy enum and error types
2. RobustStreamProcessor with three strategies
3. Partial block extraction capability
4. Comprehensive error reporting
5. All edge cases handled gracefully
6. Fuzzing test suite
7. >90% test coverage

## Success Criteria
- [ ] All documented edge cases handled
- [ ] No crashes on malformed input
- [ ] PERMISSIVE mode recovers >80% of partial blocks
- [ ] Error messages are clear and actionable
- [ ] Performance impact <10% for STRICT mode
- [ ] Fuzzing finds no crashes
- [ ] Recovery statistics available
- [ ] All strategies work correctly

## Testing Checklist
- [ ] Unit tests for each strategy
- [ ] Edge case test suite
- [ ] Partial extraction tests
- [ ] Error reporting tests
- [ ] Fuzz testing campaign
- [ ] Memory safety tests
- [ ] Performance impact tests
- [ ] Recovery statistics tests
- [ ] Integration tests with syntaxes
- [ ] Stress tests with errors
