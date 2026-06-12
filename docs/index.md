# StreamBlocks

StreamBlocks is a Python library that extracts structured, typed blocks from text streams *while they stream*, not after completion.

LLMs are good at embedding structured content (file operations, tool calls, plans) inside free-form text. StreamBlocks detects those blocks as the tokens arrive and hands you validated Pydantic objects in real time, enabling reactive agents and live UIs.

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

- **Any stream**: plain strings or native OpenAI/Anthropic/Gemini chunks, no vendor lock-in.
- **Real time**: react to a block the moment it completes, while the rest is still streaming.
- **Typed**: metadata and content are Pydantic models, validated on extraction.
- **Extensible**: custom syntaxes, adapters, block types, and framework integrations (Pydantic AI, AG-UI).

## Installation

```bash
pip install streamblocks
```

See [Installation](getting-started/installation.md) for provider extras.

[Get Started :material-arrow-right:](getting-started/quickstart.md){ .md-button .md-button--primary }
[View Examples](examples/index.md){ .md-button }
