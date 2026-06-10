# Guides

Task-oriented guides for common StreamBlocks workflows. Each guide is backed by runnable examples from the repository.

## Building blocks

- [Defining Custom Blocks](define-custom-blocks.md) — typed metadata/content models, custom parsing, JSON/YAML content.
- [Validation](validation.md) — registry validators, failure modes, early validation.
- [Error Handling](error-handling.md) — error codes, unclosed blocks, size limits.

## Connecting streams

- [OpenAI, Anthropic & Gemini](providers.md) — provider streams with auto-detected adapters.
- [AG-UI Protocol](agui.md) — bidirectional AG-UI integration.
- [Pydantic AI](pydantic-ai.md) — extract blocks from agent streams.

## Operating

- [Logging](logging.md) — stdlib, structlog, loguru, or custom loggers.
- [Performance Tuning](performance.md) — configuration knobs and trade-offs.

Looking for conceptual background instead? See [Concepts](../concepts/index.md). Complete runnable programs live in [Examples](../examples/index.md).
