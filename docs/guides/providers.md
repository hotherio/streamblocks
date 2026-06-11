# OpenAI, Anthropic & Gemini

How to extract blocks from real LLM provider streams. Each provider ships as an optional extension that registers its [input adapter](../concepts/adapters.md) for auto-detection the moment you import it.

## The pattern

The recipe is identical for all providers:

1. Install the provider extra.
2. Make sure the extension is imported (importing the provider SDK's adapter module registers it).
3. Pass the SDK's stream object **directly** to `processor.process_stream()`: no wrapper generators.

| Provider | Install | Auto-registration import | Adapter | Factory |
|----------|---------|--------------------------|---------|---------|
| Gemini | `pip install "streamblocks[gemini]"` | `import hother.streamblocks.extensions.gemini` | `GeminiInputAdapter` | `create_gemini_processor(registry)` |
| OpenAI | `pip install "streamblocks[openai]"` | `import hother.streamblocks.extensions.openai` | `OpenAIInputAdapter` | `create_openai_processor(registry)` |
| Anthropic | `pip install "streamblocks[anthropic]"` | `import hother.streamblocks.extensions.anthropic` | `AnthropicInputAdapter` | `create_anthropic_processor(registry)` |

`pip install "streamblocks[all-providers]"` installs all three SDKs at once.

Each factory takes a `Registry` and returns a `ProtocolStreamProcessor` pre-configured with that provider's input adapter and the default StreamBlocks output adapter:

```python
from hother.streamblocks.extensions.gemini import create_gemini_processor

processor = create_gemini_processor(registry)
```

The examples below use `StreamBlockProcessor` instead, which additionally passes the original provider chunks through (`emit_original_events=True`), so you keep access to usage metadata, finish reasons, and other provider-specific fields.

## Gemini: auto-detection

With the `google-genai` SDK, hand the stream straight to the processor; the adapter is detected from the first chunk (the SDK's chunk classes live under the registered `google.genai` module prefix):

```python
--8<-- "src/hother/streamblocks_examples/03_adapters/02_gemini_auto_detect.py:setup"
```

```python
--8<-- "src/hother/streamblocks_examples/03_adapters/02_gemini_auto_detect.py:example"
```

`processor.is_native_event(event)` identifies passed-through Gemini chunks without importing Gemini types in your handler code.

[View source on GitHub](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/03_adapters/02_gemini_auto_detect.py)

## OpenAI: explicit adapter

You can skip auto-detection and pass the adapter explicitly, useful when the first chunk may be ambiguous or you want zero detection overhead:

```python
--8<-- "src/hother/streamblocks_examples/03_adapters/03_openai_explicit_adapter.py:imports"
```

```python
--8<-- "src/hother/streamblocks_examples/03_adapters/03_openai_explicit_adapter.py:setup"
```

```python
--8<-- "src/hother/streamblocks_examples/03_adapters/03_openai_explicit_adapter.py:example"
```

The adapter extracts text from `choices[0].delta.content` and reports completion when `finish_reason` is set.

[View source on GitHub](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/03_adapters/03_openai_explicit_adapter.py)

## Anthropic: event-based streams

Anthropic streams discrete event types rather than uniform chunks. The adapter categorizes `content_block_delta` events as text and passes the rest (`message_delta`, `message_stop`, …) through, so nothing is lost:

```python
--8<-- "src/hother/streamblocks_examples/03_adapters/04_anthropic_adapter.py:imports"
```

```python
--8<-- "src/hother/streamblocks_examples/03_adapters/04_anthropic_adapter.py:example"
```

[View source on GitHub](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/03_adapters/04_anthropic_adapter.py)

## Handling mixed event streams

With `emit_original_events=True` your event loop sees both native provider events and StreamBlocks events in the same stream. Plain `isinstance` checks (or `processor.is_native_event()`) keep the two apart, and provider metadata stays available:

```python
--8<-- "src/hother/streamblocks_examples/03_adapters/05_mixed_event_stream.py:example"
```

[View source on GitHub](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/03_adapters/05_mixed_event_stream.py)

## A complete provider workflow

A fuller Gemini demo registers several block types behind one frontmatter [syntax](../concepts/syntaxes.md) and lets the model emit file operations, file contents, and messages in a single response:

```python
--8<-- "src/hother/streamblocks_examples/07_providers/01_gemini_simple_demo.py:setup"
```

```python
--8<-- "src/hother/streamblocks_examples/07_providers/01_gemini_simple_demo.py:example"
```

[View source on GitHub](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/07_providers/01_gemini_simple_demo.py)

!!! tip "Prompting for blocks"
    Models follow block syntax reliably when the prompt shows the exact format and explicitly forbids markdown code fences around it. See the prompts embedded in the examples above for working templates.

## Next steps

- [Adapters](../concepts/adapters.md): write an adapter for a provider that isn't built in.
- [Events](../concepts/events.md): everything your event loop can react to.
- [Extensions reference](../reference/extensions.md): full adapter and factory API per provider.
