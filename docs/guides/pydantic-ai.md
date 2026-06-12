# Pydantic AI

Extract structured blocks from a [Pydantic AI](https://ai.pydantic.dev/) agent's streaming output, in real time.

The integration lives in `hother.streamblocks.integrations.pydantic_ai` and exposes two entry points:

| Class | Use it when |
| --- | --- |
| `AgentStreamProcessor` | You already have a Pydantic AI `Agent` and want to pipe its text stream through StreamBlocks. |
| `BlockAwareAgent` | You want a single wrapper that owns both the agent and the processor and streams events directly. |

Both require the `pydantic-ai` package:

```python
--8<-- "src/hother/streamblocks_examples/06_integrations/01_pydantic_ai_integration.py:integration_imports"
```

## Teach the agent the block syntax

Block extraction only works if the model actually emits blocks, so the system prompt must show the format. Here the agent is instructed to use the [delimiter frontmatter syntax](../concepts/syntaxes.md) (`!!start` … `!!end` with a YAML header):

```python
--8<-- "src/hother/streamblocks_examples/06_integrations/01_pydantic_ai_integration.py:agent"
```

## Process the agent stream

Create a `Registry` matching the syntax you prompted for, register your block types, and wrap it in an `AgentStreamProcessor`:

```python
--8<-- "src/hother/streamblocks_examples/06_integrations/01_pydantic_ai_integration.py:setup"
```

Then feed the agent's text stream to `process_agent_stream()`. Any `AsyncIterator[str]` works; here it comes from `agent.run_stream()`:

```python
--8<-- "src/hother/streamblocks_examples/06_integrations/01_pydantic_ai_integration.py:process"
```

[View source on GitHub](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/06_integrations/01_pydantic_ai_integration.py)

Prose between blocks arrives as `TextContentEvent`, and each completed block arrives as a `BlockEndEvent` with typed `metadata` and `content`, while the agent is still streaming.

`AgentStreamProcessor` is a `StreamBlockProcessor` subclass, so it accepts the same `config` argument. It also offers `process_agent_with_events(stream, event_handler)` to invoke a callback on every event in addition to yielding it.

## Wrap everything with BlockAwareAgent

`BlockAwareAgent` bundles the agent and the processor. Pass a model name (e.g. `"openai:gpt-4o"`) or an existing `Agent` instance as `model`:

```python
from hother.streamblocks import Registry
from hother.streamblocks.core.types import BlockEndEvent
from hother.streamblocks.integrations.pydantic_ai import BlockAwareAgent

agent = BlockAwareAgent(
    registry,
    model="openai:gpt-4o",  # or an existing pydantic_ai.Agent
    system_prompt=system_prompt,
)

async for event in agent.run_with_blocks("Scaffold a FastAPI project"):
    if isinstance(event, BlockEndEvent):
        block = event.get_block()
```

`run_with_blocks()` streams the agent with `stream_text(delta=True)` and yields StreamBlocks events as blocks are detected. The wrapper stays compatible with the standard Pydantic AI interface: `run()` and `run_sync()` call straight through to the underlying agent without block extraction, and unknown attributes are forwarded to it.

## One processor, one syntax

A processor handles exactly one syntax. If your agent emits several block formats, register all block types that share a syntax in one registry, or run the captured text through a second processor with its own registry; the [full example](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/06_integrations/01_pydantic_ai_integration.py) demonstrates the two-pass approach.

## Next steps

- [Events](../reference/events.md): every event type the processor can emit.
- [Providers guide](providers.md): process raw OpenAI, Anthropic, or Gemini streams without an agent framework.
- [Performance Tuning](performance.md): trim event volume for high-throughput agent streams.
