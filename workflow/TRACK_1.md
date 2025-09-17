# Track 1: Block Models and Candidate System

**Status: ✅ COMPLETED**

## Overview
Implement the block tracking system including candidates, extracted blocks, and the registry foundation.

## TODO List

### BlockCandidate Implementation
- [x] Update core/models.py (replace stub)
  - [x] Import required types from core.types
  - [x] Define BlockCandidate class
    - [x] Constructor params: syntax (BlockSyntax), start_line (int)
    - [x] Instance variables:
      - [x] self.syntax = syntax
      - [x] self.start_line = start_line
      - [x] self.lines: list[str] = []
      - [x] self.state = BlockState.HEADER_DETECTED
      - [x] self.metadata_lines: list[str] = []
      - [x] self.content_lines: list[str] = []
      - [x] self.current_section: str = "header"
    - [x] Implement add_line(line: str) -> None
    - [x] Implement @property raw_text -> str (joins lines with \n)
    - [x] Implement compute_hash() -> str
      - [x] Use first 64 chars of raw_text
      - [x] SHA256 hash, return first 8 chars of hex
    - [x] Add comprehensive docstrings

### Block Model
- [x] Create Block model in core/models.py
  - [x] Inherit from BaseModel and Generic[TMetadata, TContent]
  - [x] Fields:
    - [x] syntax_name: str
    - [x] metadata: TMetadata
    - [x] content: TContent
    - [x] raw_text: str
    - [x] line_start: int
    - [x] line_end: int
    - [x] hash_id: str
  - [x] Add field descriptions
  - [x] Add model validation
  - [x] Add comprehensive docstring

### Registry Foundation
- [x] Create core/registry.py
  - [x] Define BlockType type alias (str)
  - [x] Define BlockRegistry class
    - [x] Instance variables:
      - [x] _syntaxes: dict[str, BlockSyntax] = {}
      - [x] _block_types: dict[BlockType, list[BlockSyntax]] = {}
      - [x] _validators: dict[BlockType, list[Callable]] = {}
      - [x] _priority_order: list[str] = []
    - [x] Implement register_syntax method (basic version)
      - [x] Parameters: syntax, block_types, priority
      - [x] Check for duplicate names
      - [x] Store syntax reference
    - [x] Implement get_syntaxes method
      - [x] Return syntaxes in priority order
    - [x] Add placeholder methods for future tracks
    - [x] Add comprehensive docstrings

### Content Model Examples
- [x] Create content/ directory
  - [x] Create content/__init__.py
  - [x] Create content/base.py
    - [x] Define base content models if needed
  - [x] Create content/files.py
    - [x] Define FileOperation model
      - [x] action: Literal["create", "edit", "delete"]
      - [x] path: str
    - [x] Define FileOperationsContent model
      - [x] operations: list[FileOperation]
      - [x] Implement parse classmethod
        - [x] Parse "path:action" format
        - [x] Map C/E/D to create/edit/delete
        - [x] Handle errors gracefully
    - [x] Define FileOperationsMetadata model
      - [x] id: str
      - [x] block_type: Literal["files_operations"]
      - [x] description: str | None = None
  - [x] Create content/patch.py
    - [x] Define PatchContent model
      - [x] diff: str
      - [x] Implement parse classmethod
        - [x] Validate unified diff format
        - [x] Check for @@ markers
    - [x] Define PatchMetadata model
      - [x] id: str
      - [x] block_type: Literal["patch"]
      - [x] file_path: str
      - [x] description: str | None = None

### Testing
- [x] Create tests/unit/test_models.py
  - [x] Test BlockCandidate
    - [x] Test initialization
    - [x] Test add_line functionality
    - [x] Test raw_text property
    - [x] Test hash computation consistency
    - [x] Test state transitions
    - [x] Test with empty content
    - [x] Test with large content
  - [x] Test Block model
    - [x] Test creation with valid data
    - [x] Test serialization/deserialization
    - [x] Test with generic types
    - [x] Test field validation
  - [x] Test example content models
    - [x] Test FileOperationsContent.parse
    - [x] Test PatchContent.parse
    - [x] Test error cases
- [x] Create tests/unit/test_registry.py
  - [x] Test basic registry operations
    - [x] Test syntax registration
    - [x] Test duplicate name detection
    - [x] Test priority ordering
    - [x] Test get_syntaxes
- [x] Create tests/integration/test_models_integration.py
  - [x] Test BlockCandidate with mock syntax
  - [x] Test Block with real metadata/content types
  - [x] Test registry with multiple syntaxes

### Update Core Exports
- [x] Update core/__init__.py
  - [x] Export BlockCandidate
  - [x] Export Block
  - [x] Export BlockRegistry
  - [x] Export content models

### Documentation
- [x] Document BlockCandidate lifecycle
- [x] Document Block model usage
- [x] Document registry patterns
- [x] Add examples for content models

### Type Checking and Quality
- [x] Run mypy on all new code
- [x] Fix any type errors
- [x] Run ruff linter and formatter
- [x] Ensure >95% test coverage

## Deliverables
1. Complete BlockCandidate implementation with state tracking
2. Block model for validated blocks
3. Basic BlockRegistry implementation
4. Example content models (FileOperations, Patch)
5. Comprehensive test suite with >95% coverage

## Success Criteria
- [x] BlockCandidate tracks state and accumulates lines correctly
- [x] Block model validates and serializes properly
- [x] Hash IDs are consistent for same content
- [x] Registry can store and retrieve syntaxes by priority
- [x] Content models parse their formats correctly
- [x] All tests pass with >95% coverage
- [x] Type checking passes in strict mode
- [x] Code is properly documented

## Testing Checklist
- [x] Unit tests for BlockCandidate methods
- [x] Unit tests for BlockCandidate state transitions
- [x] Unit tests for hash computation
- [x] Unit tests for Block model creation
- [x] Unit tests for Block serialization
- [x] Unit tests for content parsing
- [x] Unit tests for registry operations
- [x] Property tests for hash consistency
- [x] Edge case tests (empty blocks, huge blocks)
- [x] Integration tests with type system
- [ ] Performance baseline for model creation (not needed per user feedback)
- [ ] Memory usage tests for large candidates (not needed per user feedback)
