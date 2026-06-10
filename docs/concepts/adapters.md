# Adapters

LLM SDKs don't stream plain strings — they stream provider-specific event objects (OpenAI `ChatCompletionChunk`, Anthropic `ContentBlockDeltaEvent`, Gemini `GenerateContentResponse`, …). Adapters bridge that gap: an **input adapter** extracts text from incoming events, an **output adapter** converts StreamBlocks [events](events.md) into whatever format your application emits.

## Plain text needs nothing

Strings are handled by the built-in `IdentityInputAdapter`, selected automatically — any `AsyncIterator[str]` just works:

```python
--8<-- "src/hother/streamblocks_examples/03_adapters/01_identity_adapter_plain_text.py:example"
```

[View source on GitHub](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/03_adapters/01_identity_adapter_plain_text.py)

## The InputProtocolAdapter protocol

An input adapter is any object satisfying the `InputProtocolAdapter` protocol — no inheritance required:

| Method | Required | Purpose |
|--------|----------|---------|
| `categorize(event) -> EventCategory` | yes | Route the event: process its text, pass it through, or drop it |
| `extract_text(event) -> str \| None` | yes | Pull the text out of a `TEXT_CONTENT` event |
| `get_metadata(event) -> dict \| None` | no | Extract protocol-specific metadata (defaults to `None`) |
| `is_complete(event) -> bool` | no | Signal stream completion (defaults to `False`) |

`EventCategory` is exhaustive — every event falls into one of three buckets:

| Category | Meaning |
|----------|---------|
| `TEXT_CONTENT` | Event contains text; extract it and run block detection |
| `PASSTHROUGH` | No text; forward the event unchanged to the output |
| `SKIP` | Drop the event entirely |

A minimal adapter for dict-shaped chunks:

```python
--8<-- "src/hother/streamblocks_examples/03_adapters/10_callable_adapter.py:adapter"
```

Pass it explicitly to bypass detection:

```python
--8<-- "src/hother/streamblocks_examples/03_adapters/10_callable_adapter.py:example"
```

[View source on GitHub](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/03_adapters/10_callable_adapter.py)

For objects where the text simply lives in one attribute, skip the custom class and use the built-in `AttributeInputAdapter`:

```python
--8<-- "src/hother/streamblocks_examples/03_adapters/11_attribute_adapter_generic.py:example"
```

## Auto-detection

When no adapter is passed (and `auto_detect_adapter=True`, the default), `InputAdapterRegistry.detect()` inspects the first chunk and picks an adapter in this order:

1. `str` → `IdentityInputAdapter`
2. **Module prefix match** — the chunk class's `__module__` is matched against registered prefixes (e.g. `"openai.types"`, `"google.genai"`, `"anthropic."`)
3. **Attribute pattern match** — registered duck-typing patterns (e.g. `["text", "candidates"]` for Gemini)
4. **Fallback** — objects with a `text` or `content` attribute get an `AttributeInputAdapter`
5. No match → `None` (`detect_input_adapter()` raises `ValueError` with the list of registered prefixes)

Provider [extensions](../guides/providers.md) self-register on import — `import hother.streamblocks.extensions.openai` is enough to make auto-detection work for OpenAI streams.

### Registering a custom adapter

Define the adapter for your format:

```python
--8<-- "src/hother/streamblocks_examples/03_adapters/09_custom_adapter.py:adapter"
```

Then register it by module prefix so auto-detection picks it up:

```python
--8<-- "src/hother/streamblocks_examples/03_adapters/09_custom_adapter.py:register"
```

You can also register with the `@InputAdapterRegistry.register(module_prefix=..., attributes=...)` decorator, or `InputAdapterRegistry.register_pattern()` for attribute-based detection.

[View source on GitHub](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/03_adapters/09_custom_adapter.py)

## Output adapters

An `OutputProtocolAdapter` transforms StreamBlocks events into your target format:

| Method | Purpose |
|--------|---------|
| `to_protocol_event(event) -> TOutput \| list[TOutput] \| None` | Convert a StreamBlocks event; return a list to fan out, `None` to filter |
| `passthrough(original_event) -> TOutput \| None` | Handle events the input adapter categorized as `PASSTHROUGH` |

```python
--8<-- "src/hother/streamblocks_examples/03_adapters/17_custom_output_adapter.py:output_adapter"
```

[View source on GitHub](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/03_adapters/17_custom_output_adapter.py)

The default is `StreamBlocksOutputAdapter`, which passes native StreamBlocks events through unchanged. The `BidirectionalAdapter` protocol bundles an input and an output adapter behind `input_adapter` / `output_adapter` properties when you want to ship both as one object.

## Two processors

| Processor | Input | Output | Use when |
|-----------|-------|--------|----------|
| `StreamBlockProcessor` | Any stream (adapter auto-detected or passed via `process_stream(stream, adapter=...)`) | Native StreamBlocks events, interleaved with original chunks if `emit_original_events=True` | You consume StreamBlocks events directly — the common case |
| `ProtocolStreamProcessor[TInput, TOutput]` | Any stream | Your protocol's event type via an output adapter | You translate between protocols end to end (e.g. [AG-UI](../guides/agui.md)) |

`ProtocolStreamProcessor` wires both directions together:

```python
--8<-- "src/hother/streamblocks_examples/03_adapters/16_bidirectional_protocol.py:setup"
```

`PASSTHROUGH` input events reach the output adapter's `passthrough()`; `SKIP` events vanish; text flows through block detection and comes out as transformed events:

```python
--8<-- "src/hother/streamblocks_examples/03_adapters/16_bidirectional_protocol.py:stream"
```

[View source on GitHub](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/03_adapters/16_bidirectional_protocol.py)

## Next steps

- [OpenAI, Anthropic & Gemini guide](../guides/providers.md) — the provider extensions in practice.
- [Events](events.md) — what the processor emits once text is extracted.
- [Adapters reference](../reference/adapters.md) — full protocol and registry API.
