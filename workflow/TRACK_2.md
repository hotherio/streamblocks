# Track 2: Syntax Framework Implementation

## Overview
Build the complete framework for syntax implementations, focusing on the protocol and base classes.

## TODO List

### Enhance BlockSyntax Protocol
- [ ] Review and finalize core/types.py BlockSyntax protocol
  - [ ] Ensure all method signatures are correct
  - [ ] Verify generic type constraints
  - [ ] Add any missing type hints
  - [ ] Enhance docstrings with examples

### Create Syntax Base Module
- [ ] Create syntaxes/ directory
  - [ ] Create syntaxes/__init__.py
  - [ ] Create syntaxes/base.py
    - [ ] Re-export BlockSyntax protocol
    - [ ] Re-export DetectionResult
    - [ ] Re-export ParseResult
    - [ ] Create utility functions for syntax helpers

### Abstract Base Classes
- [ ] Create syntaxes/abc.py
  - [ ] Define BaseSyntax abstract class
    - [ ] Implement common functionality
    - [ ] Provide default validate_block implementation
    - [ ] Add helper methods for subclasses
  - [ ] Define FrontmatterSyntax abstract class
    - [ ] Common logic for frontmatter-style syntaxes
    - [ ] YAML parsing helpers
    - [ ] Metadata section detection
  - [ ] Define DelimiterSyntax abstract class
    - [ ] Common logic for delimiter-based syntaxes
    - [ ] Opening/closing pattern helpers
    - [ ] Line matching utilities

### Syntax Utilities
- [ ] Create syntaxes/utils.py
  - [ ] Pattern building helpers
    - [ ] escape_delimiter(delimiter: str) -> str
    - [ ] build_opening_pattern(delimiter: str) -> Pattern
    - [ ] build_closing_pattern(delimiter: str) -> Pattern
  - [ ] Metadata extraction helpers
    - [ ] parse_inline_metadata(line: str, pattern: Pattern) -> dict
    - [ ] parse_yaml_metadata(lines: list[str]) -> dict
  - [ ] Content processing helpers
    - [ ] strip_markers(lines: list[str]) -> list[str]
    - [ ] validate_yaml_format(text: str) -> bool

### Enhanced Registry Implementation
- [ ] Update core/registry.py
  - [ ] Enhance register_syntax method
    - [ ] Validate syntax has required attributes
    - [ ] Handle priority insertion correctly
    - [ ] Update block type mappings
  - [ ] Implement unregister_syntax method
    - [ ] Remove from all internal structures
    - [ ] Handle missing syntax gracefully
  - [ ] Implement get_syntax_by_name method
  - [ ] Implement get_syntaxes_for_block_type method
  - [ ] Add syntax priority management
    - [ ] reorder_syntaxes method
    - [ ] set_syntax_priority method

### Testing Framework
- [ ] Create tests/unit/test_syntax_framework.py
  - [ ] Test abstract base classes
    - [ ] Test BaseSyntax defaults
    - [ ] Test FrontmatterSyntax helpers
    - [ ] Test DelimiterSyntax helpers
  - [ ] Test syntax utilities
    - [ ] Test pattern builders
    - [ ] Test metadata extractors
    - [ ] Test content processors
  - [ ] Create comprehensive mock syntaxes
    - [ ] SimpleMockSyntax
    - [ ] ComplexMockSyntax
    - [ ] FailingMockSyntax
  - [ ] Test protocol compliance
- [ ] Create tests/unit/test_registry_advanced.py
  - [ ] Test syntax validation on registration
  - [ ] Test priority ordering
  - [ ] Test unregistration
  - [ ] Test block type queries
  - [ ] Test concurrent registration

### Example Mock Implementation
- [ ] Create syntaxes/mock.py (for testing)
  - [ ] Define MockSyntax class
    - [ ] Implements BlockSyntax protocol
    - [ ] Configurable behavior
    - [ ] Useful for testing processor
  - [ ] Define MockMetadata model
  - [ ] Define MockContent model
  - [ ] Add detection patterns
  - [ ] Add parsing logic

### Documentation
- [ ] Create syntax implementation guide
  - [ ] How to implement BlockSyntax
  - [ ] When to use base classes
  - [ ] Common patterns and anti-patterns
  - [ ] Performance considerations
- [ ] Document registry usage
  - [ ] Registration patterns
  - [ ] Priority management
  - [ ] Dynamic syntax loading

### Performance Optimization Hooks
- [ ] Add optimization hints to BlockSyntax
  - [ ] Optional get_opening_hints() method
  - [ ] Optional get_quick_reject_pattern() method
  - [ ] Document performance implications

### Type Checking and Quality
- [ ] Run mypy on all syntax code
- [ ] Verify protocol variance
- [ ] Check ABC method signatures
- [ ] Run ruff linter and formatter
- [ ] Ensure >95% test coverage

## Deliverables
1. Complete BlockSyntax protocol with all methods
2. Abstract base classes for common syntax patterns
3. Utility functions for syntax implementations
4. Enhanced registry with full functionality
5. Comprehensive mock implementations for testing
6. >95% test coverage

## Success Criteria
- [ ] BlockSyntax protocol is complete and well-documented
- [ ] Base classes reduce boilerplate significantly
- [ ] Mock syntaxes demonstrate proper implementation
- [ ] Registry handles all syntax operations correctly
- [ ] Priority system works as expected
- [ ] Utilities cover common parsing needs
- [ ] All tests pass with >95% coverage
- [ ] Type checking passes in strict mode

## Testing Checklist
- [ ] Unit tests for all base classes
- [ ] Unit tests for all utilities
- [ ] Mock syntax implementation tests
- [ ] Protocol compliance verification
- [ ] Registry operation tests
- [ ] Priority ordering tests
- [ ] Concurrent access tests
- [ ] Error handling tests
- [ ] Performance tests for pattern matching
- [ ] Memory tests for syntax storage
- [ ] Integration tests with Track 0-1 components
