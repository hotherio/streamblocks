# API Reference

Complete API documentation for StreamBlocks.

## Modules

### [Core](core.md)

Core components and the main processor:

- `StreamBlockProcessor` - Main processing engine
- `StreamEvent` - Event data class
- `EventType` - Event type enumeration
- `BlockState` - Block state enumeration

### [Syntaxes](syntaxes.md)

Block syntax definitions:

- `BaseSyntax` - Base class for syntaxes
- `MarkdownFrontmatterSyntax` - YAML frontmatter syntax
- `DelimiterFrontmatterSyntax` - Custom delimiter syntax
- `FencedCodeSyntax` - Markdown code blocks

### [Adapters](adapters.md)

Stream adapters for AI providers:

- `BaseAdapter` - Base adapter class
- `GeminiAdapter` - Google Gemini adapter
- `OpenAIAdapter` - OpenAI adapter
- `AnthropicAdapter` - Anthropic adapter
- `auto_detect_adapter` - Automatic adapter detection

### [Blocks](blocks.md)

Block type definitions:

- `Block` - Base block model
- `BlockCandidate` - Block parsing candidate
- `MessageBlock` - Message content block
- `ToolCallBlock` - Tool call block

## Quick Links

- [Getting Started](../getting_started.md)
- [Examples](../examples/index.md)
- [Patterns](../patterns.md)
