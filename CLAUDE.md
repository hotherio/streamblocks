# StreamBlocks Development Progress

## Project Overview
StreamBlocks is a Python 3.13+ library for real-time extraction and processing of structured blocks from text streams.

## Progress Summary

### Completed Tracks

#### Track 0: Core Foundation and Types ✅
- Set up project structure with proper packaging
- Defined core types and enums in `src/streamblocks/core/types.py`
- Created EventType and BlockState enums
- Defined StreamEvent, DetectionResult, and ParseResult data classes
- Established the BlockSyntax protocol with generic types

#### Track 1: Block Models and Candidate System ✅
- Implemented BlockCandidate and Block models in `src/streamblocks/core/models.py`
- Created the BlockRegistry foundation in `src/streamblocks/core/registry.py`
- Added support for priority-based syntax registration
- Implemented block validation framework

#### Track 2: Syntax Framework ✅
- Completed BlockSyntax protocol implementation
- Created BaseSyntax abstract class in `src/streamblocks/syntaxes/base.py`
- Added RegexSyntax class for regex-based parsing
- Implemented utility functions for syntax creation

#### Track 3: Built-in Syntaxes ✅
- Implemented FrontmatterSyntax for YAML/TOML frontmatter blocks
- Created PreambleSyntax for Hugo-style preamble blocks
- Added FencedCodeSyntax for Markdown code blocks
- All syntaxes properly handle metadata and content parsing

#### Track 4: Stream Processing Engine ✅
- Implemented StreamBlockProcessor in `src/streamblocks/core/processor.py`
- Added async stream processing with proper line accumulation
- Implemented event generation for all processing stages
- Added block candidate management and size limit enforcement

### Key Implementation Details

#### Type System
- Uses Python 3.13+ generic types extensively
- All components are fully typed with proper annotations
- No use of type: ignore or noqa comments

#### Architecture
- Event-driven architecture with StreamEvent types
- State machine approach for block detection
- Async/await pattern for stream processing
- Registry pattern for syntax management

#### Testing Approach
- Tests located in `tests/` directory
- Using pytest with async support
- Property-based testing with hypothesis where appropriate

### Next Steps
1. Run tests for Track 4 implementation
2. Continue with remaining tracks as directed
3. Never move to another track before being told to do so
4. Never use # type: ignore or # noqa instructions

### Important Commands
```bash
# Run pre-commit hooks
uv run lefthook run pre-commit --all-files -- --no-stash

# Run tests
uv run pytest

# Run specific test file
uv run pytest tests/test_processor.py
```
- Similarily to pytest for the tests, it is important to check that all examples pass without issue using: uv run python examples/run_examples.py
See @examples/README.md for more information on the example runner.
