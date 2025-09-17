# Track 3: Built-in Syntax Implementations

## Overview
Implement the three default syntax parsers as specified in the requirements.

## TODO List

### DelimiterPreambleSyntax Implementation
- [ ] Create syntaxes/delimiter.py
  - [ ] Import required types and base classes
  - [ ] Define DelimiterPreambleSyntax class
    - [ ] Generic over TMetadata, TContent
    - [ ] Constructor parameters:
      - [ ] metadata_class: type[TMetadata]
      - [ ] content_class: type[TContent]
      - [ ] delimiter: str = "!!"
    - [ ] Instance variables:
      - [ ] Store metadata_class and content_class
      - [ ] Create _opening_pattern regex: ^{delimiter}(\w+):(\w+)(:.+)?$
      - [ ] Create _closing_pattern regex: ^{delimiter}end$
    - [ ] Implement @property name
      - [ ] Return f"delimiter_preamble_{delimiter}"
    - [ ] Implement detect_line method
      - [ ] If context is None: check for opening pattern
        - [ ] Extract id, block_type, optional params
        - [ ] Return DetectionResult with inline metadata
      - [ ] If context exists: check for closing pattern
        - [ ] Return DetectionResult(is_closing=True)
    - [ ] Implement should_accumulate_metadata
      - [ ] Always return False (metadata is inline)
    - [ ] Implement parse_block
      - [ ] Re-parse first line for metadata
      - [ ] Extract content from lines[1:-1]
      - [ ] Instantiate metadata_class
      - [ ] Parse content using content_class
      - [ ] Handle errors appropriately
    - [ ] Implement validate_block (use default)

### MarkdownFrontmatterSyntax Implementation
- [ ] Create syntaxes/frontmatter.py
  - [ ] Import required types and yaml
  - [ ] Define MarkdownFrontmatterSyntax class
    - [ ] Generic over TMetadata, TContent
    - [ ] Constructor parameters:
      - [ ] metadata_class: type[TMetadata]
      - [ ] content_class: type[TContent]
      - [ ] fence: str = "```"
      - [ ] info_string: str | None = None
    - [ ] Instance variables:
      - [ ] Store all parameters
      - [ ] Create _fence_pattern based on fence and info_string
      - [ ] Create _frontmatter_pattern: ^---$
    - [ ] Implement @property name
      - [ ] Return f"markdown_frontmatter_{info_string}" or "markdown_frontmatter"
    - [ ] Implement detect_line method
      - [ ] If context is None: check for fence pattern
      - [ ] If context exists:
        - [ ] In "header" section: check for frontmatter start
        - [ ] In "metadata" section: check for frontmatter end or accumulate
        - [ ] In "content" section: check for closing fence or accumulate
    - [ ] Implement should_accumulate_metadata
      - [ ] Return True if in "header" or "metadata" section
    - [ ] Implement parse_block
      - [ ] Parse YAML from metadata_lines
      - [ ] Instantiate metadata_class
      - [ ] Parse content from content_lines
      - [ ] Handle YAML errors
    - [ ] Implement validate_block (use default or enhance)

### DelimiterFrontmatterSyntax Implementation
- [ ] Create syntaxes/hybrid.py
  - [ ] Import required types and yaml
  - [ ] Define DelimiterFrontmatterSyntax class
    - [ ] Generic over TMetadata, TContent
    - [ ] Constructor parameters:
      - [ ] metadata_class: type[TMetadata]
      - [ ] content_class: type[TContent]
      - [ ] start_delimiter: str = "!!start"
      - [ ] end_delimiter: str = "!!end"
    - [ ] Instance variables:
      - [ ] Store all parameters
      - [ ] Create _frontmatter_pattern: ^---$
    - [ ] Implement @property name
      - [ ] Return f"delimiter_frontmatter_{start_delimiter}"
    - [ ] Implement detect_line method
      - [ ] If context is None: check for start_delimiter
      - [ ] If context exists:
        - [ ] In "header" section: check for frontmatter or move to content
        - [ ] In "metadata" section: check for frontmatter end or accumulate
        - [ ] In "content" section: check for end_delimiter or accumulate
    - [ ] Implement should_accumulate_metadata
      - [ ] Return True if in "header" or "metadata" section
    - [ ] Implement parse_block
      - [ ] Similar to MarkdownFrontmatterSyntax
      - [ ] Parse YAML metadata
      - [ ] Parse content
      - [ ] Handle errors

### Update Syntax Exports
- [ ] Update syntaxes/__init__.py
  - [ ] Export DelimiterPreambleSyntax
  - [ ] Export MarkdownFrontmatterSyntax
  - [ ] Export DelimiterFrontmatterSyntax

### Comprehensive Testing
- [ ] Create tests/unit/test_delimiter_syntax.py
  - [ ] Test with FileOperations content
    - [ ] Valid block with all operations
    - [ ] Block with inline parameters
    - [ ] Empty content block
    - [ ] Missing closing marker
    - [ ] Invalid metadata format
  - [ ] Test with Patch content
    - [ ] Valid patch block
    - [ ] Invalid patch format
  - [ ] Edge cases:
    - [ ] Delimiter in content
    - [ ] Nested-looking blocks
    - [ ] Very long metadata line
- [ ] Create tests/unit/test_frontmatter_syntax.py
  - [ ] Test basic markdown blocks
    - [ ] With frontmatter
    - [ ] Without frontmatter
    - [ ] With info string
    - [ ] Empty frontmatter
  - [ ] Test YAML parsing
    - [ ] Valid YAML
    - [ ] Invalid YAML
    - [ ] Complex nested structures
  - [ ] Edge cases:
    - [ ] Triple backticks in content
    - [ ] Frontmatter markers in content
- [ ] Create tests/unit/test_hybrid_syntax.py
  - [ ] Test delimiter + frontmatter
    - [ ] Valid blocks
    - [ ] Missing frontmatter
    - [ ] Invalid YAML
  - [ ] Edge cases similar to above
- [ ] Create tests/integration/test_syntax_compatibility.py
  - [ ] Test all syntaxes with same content
  - [ ] Verify consistent parsing
  - [ ] Test syntax priority

### Performance Testing
- [ ] Create benchmarks/syntax_performance.py
  - [ ] Benchmark regex compilation
  - [ ] Benchmark line detection
  - [ ] Benchmark parsing speed
  - [ ] Compare syntax performance
  - [ ] Test with large blocks

### Documentation and Examples
- [ ] Add docstrings to all classes
- [ ] Create examples/ directory
  - [ ] Create examples/syntax_examples.py
    - [ ] Show all three syntaxes
    - [ ] Same content, different formats
    - [ ] Error handling examples

### Type Checking and Quality
- [ ] Run mypy on all syntax implementations
- [ ] Verify generic constraints
- [ ] Run ruff linter and formatter
- [ ] Ensure >95% test coverage

## Deliverables
1. DelimiterPreambleSyntax with inline metadata parsing
2. MarkdownFrontmatterSyntax with YAML support
3. DelimiterFrontmatterSyntax hybrid implementation
4. Comprehensive test suite for all syntaxes
5. Performance benchmarks
6. Usage examples

## Success Criteria
- [ ] All syntaxes parse their respective formats correctly
- [ ] Inline metadata extraction works for delimiter syntax
- [ ] YAML parsing works for frontmatter syntaxes
- [ ] Empty blocks handled gracefully
- [ ] Malformed blocks produce clear errors
- [ ] Each syntax can work with any metadata/content models
- [ ] Performance is acceptable (<1ms per block)
- [ ] >95% test coverage achieved
- [ ] All edge cases handled

## Testing Checklist
- [ ] Unit tests for each syntax class
- [ ] Tests for all detection patterns
- [ ] Tests for metadata extraction
- [ ] Tests for content parsing
- [ ] Tests for error conditions
- [ ] Tests for edge cases
- [ ] Fuzz testing with random input
- [ ] Performance benchmarks
- [ ] Memory usage tests
- [ ] Integration tests with registry
- [ ] Cross-syntax compatibility tests
