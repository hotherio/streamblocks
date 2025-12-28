# Changelog

All notable changes to this project will be documented in this file.

## [unreleased]

### ⚙️ Miscellaneous Tasks

- Update uv.lock with project dependencies
- Add sandbox example implementation
- Remove old workflow tracking files
- Remove py.typed marker file
- **lock**: Update lock file

### 🎨 Styling

- Apply linter formatting (TRACK 0)
- Fix quote style in test_protocol.py (TRACK 0)

### 🐛 Bug Fixes

- Update lefthook config and add type annotations (TRACK 0)
- Resolve linting issues in FileOperationsContent
- **syntax**: Update delimiter patterns to allow indented markers
- Resolve all type errors and add comprehensive ruff per-file-ignores
- **types**: Update StreamEvent forward reference from Block to BlockDefinition
- Type hinting
- **ci**: Update lefthook hooks to use uv run and python3
- **types**: Resolve basedpyright errors in blocks and parsing decorators
- **type**: Avoid the usage of cast when unecessary

### 📚 Documentation

- Update README for streamblocks project (TRACK 0)
- Add streamblocks prototype and workflow documentation
- **examples**: Add examples demonstrating simplified API
- Update README for simplified API
- Update CLAUDE.md with project notes

### 📦 Build

- Configure pytest for better test discovery

### 🔨 Refactor

- Remove template hother files (TRACK 0)
- Use StrEnum for action codes in FileOperationsContent
- [**breaking**] Make built-in syntaxes generic with user-provided models
- **content**: Update content models to inherit from BaseContent
- **types**: Update type definitions and exports
- **core**: Add protocols module for type safety
- **syntaxes**: Remove old syntax implementations
- **core**: Simplify processor and registry implementations
- **api**: Simplify API and add comprehensive documentation
- **syntax**: Replace Any with Pydantic BaseModel in syntax classes
- **registry**: Remove BlockRegistry backward compatibility alias
- **api**: [**breaking**] Aggregate metadata and content into BlockDefinition
- **api**: Separate metadata and data fields in Block
- **api**: [**breaking**] Simplify syntax initialization to use single block_class parameter
- **registry**: [**breaking**] Separate syntax format from block type mapping
- **models**: [**breaking**] Eliminate BlockDefinition field duplication
- Improve examples structure

### 🚀 Features

- **core**: Implement core types and protocols (TRACK 0)
- Implement BlockCandidate and Block models
- Implement BlockRegistry for managing syntax parsers
- Add content models for file operations and patches
- Export new core components from __init__
- Implement Track 3 - Built-in Syntaxes
- Implement stream processing engine (Track 4)
- **core**: Add BaseMetadata and BaseContent base classes
- **syntaxes**: Add simplified syntax implementations with optional models
- **content**: Add FileContentMetadata and FileContentContent classes
- **content**: Add MessageMetadata and MessageContent for AI communication
- **integrations**: Add PydanticAI integration for AI agent support
- **content**: Add interactive blocks for UI components and forms
- **content**: Add visualization, memory, and toolcall content types
- **examples**: Add comprehensive examples for new features
- **blocks**: Add structured output blocks with dynamic Pydantic schemas
- Aliases on the default blocks
- **logger**: Add support for loggers
- **adapters**: Add stream adapter system with provider support (#4)
- **core**: [**breaking**] Add section events and block state machine (#6)
- **adapters**: Add bidirectional adapter system with provider support (#7)

### 🧪 Testing

- **core**: Add comprehensive unit tests (TRACK 0)
- Add unit tests for models, registry, and content
- Add integration tests for models with real syntaxes
- Add validate_block method to protocol tests
- Add tests for base classes and minimal API
- Remove old test files
