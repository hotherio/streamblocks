# StreamBlocks

**Real-time extraction of structured blocks from AI text streams**

StreamBlocks is a Python library for detecting and extracting structured content blocks from streaming text. Extract semantic blocks as they stream, not after completion, enabling reactive AI agents and real-time processing.

<div class="grid cards" markdown>

-   :material-lightning-bolt:{ .lg .middle } **Stream Processing**

    ---

    Extract blocks in real-time as text streams, enabling immediate reactions and feedback loops with LLMs.

    [:octicons-arrow-right-24: Getting Started](getting-started/index.md)

-   :material-puzzle:{ .lg .middle } **Multiple Syntaxes**

    ---

    Choose from delimiter-based, Markdown frontmatter, or create custom syntaxes for your use case.

    [:octicons-arrow-right-24: Syntaxes](concepts/syntaxes.md)

-   :material-connection:{ .lg .middle } **Provider Adapters**

    ---

    Works with Gemini, OpenAI, Anthropic out of the box. Easy to add custom adapters.

    [:octicons-arrow-right-24: Adapters](concepts/adapters.md)

-   :material-shield-check:{ .lg .middle } **Type Safe**

    ---

    Full Pydantic model support with validation. Define your block metadata and content with type safety.

    [:octicons-arrow-right-24: Blocks & Registry](concepts/blocks-and-registry.md)

</div>

## Quick Example

```python
--8<-- "src/hother/streamblocks_examples/00_quickstart/01_hello_world.py:imports"

--8<-- "src/hother/streamblocks_examples/00_quickstart/01_hello_world.py:example"
```

The processor consumes any async text stream and emits [events](concepts/events.md) as it detects, accumulates, and completes blocks. When a block closes, `BlockEndEvent.get_block()` returns the fully parsed, validated, typed block.

## Why StreamBlocks?

| Feature | Benefit |
|---------|---------|
| **LLM Agnostic** | Works with any text stream, no vendor lock-in |
| **Real-time Processing** | React to blocks as they stream, don't wait for completion |
| **Type Safety** | Pydantic models for metadata and content validation |
| **Extensible** | Custom syntaxes, adapters, and block types |
| **Framework Compatible** | Integrates with Pydantic AI, AG-UI, and others |

## Installation

```bash
pip install streamblocks
```

With provider support:

```bash
pip install streamblocks[all-providers]
```

See [Installation](getting-started/installation.md) for all extras.

[Get Started :material-arrow-right:](getting-started/quickstart.md){ .md-button .md-button--primary }
[View Examples](examples/index.md){ .md-button }
