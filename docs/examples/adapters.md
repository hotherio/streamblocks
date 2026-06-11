# Adapters Examples

Adapters extract text from provider-specific stream chunks (Gemini, OpenAI, Anthropic, or your own format) and shape what events the processor emits. See the [Adapters concept page](../concepts/adapters.md) for background. Most examples here run offline; the ones hitting real provider APIs are flagged with the required key.

## Identity Adapter (Plain Text)

The default behavior: plain text streams need no adapter at all; chunks pass straight through to block detection.

#! src/hother/streamblocks_examples/03_adapters/01_identity_adapter_plain_text.py

## Gemini Auto-Detect

Requires `GEMINI_API_KEY` (or `GOOGLE_API_KEY`). StreamBlocks automatically detects Gemini chunks and extracts their text; no explicit adapter configuration needed.

#! src/hother/streamblocks_examples/03_adapters/02_gemini_auto_detect.py

## OpenAI Explicit Adapter

Requires `OPENAI_API_KEY`. Configures an explicit adapter for OpenAI streams and shows how to access provider fields like `finish_reason` from the original chunks.

#! src/hother/streamblocks_examples/03_adapters/03_openai_explicit_adapter.py

## Anthropic Adapter

Requires `ANTHROPIC_API_KEY`. Handles Anthropic's event-based streaming format, where different event types (`content_block_delta`, `message_stop`, ...) are preserved alongside extraction.

#! src/hother/streamblocks_examples/03_adapters/04_anthropic_adapter.py

## Mixed Event Stream

Handles a stream containing both original provider chunks and StreamBlocks events, with `isinstance`-based type-checking patterns to route each kind.

#! src/hother/streamblocks_examples/03_adapters/05_mixed_event_stream.py

## Text Delta Streaming

Character-by-character streaming with `TextDeltaEvent`, useful for typewriter effects and live progress indicators.

#! src/hother/streamblocks_examples/03_adapters/06_text_delta_streaming.py

## Block Opened Event

Uses `BlockOpenedEvent` to prepare UI elements or resources before any block content arrives, the earliest signal that a block is starting.

#! src/hother/streamblocks_examples/03_adapters/07_block_opened_event.py

## Configuration Flags

A tour of `ProcessorConfig` options, `emit_original_events`, `emit_text_deltas`, and `auto_detect_adapter`, and how each changes the emitted event stream.

#! src/hother/streamblocks_examples/03_adapters/08_configuration_flags.py

## Custom Adapter

Creates a custom input adapter for a proprietary streaming format and registers it for auto-detection, so downstream code never sees the raw chunks.

#! src/hother/streamblocks_examples/03_adapters/09_custom_adapter.py

## Callable Adapter

A simple inline input adapter class for quick custom extraction, handy when a full adapter implementation would be overkill.

#! src/hother/streamblocks_examples/03_adapters/10_callable_adapter.py

## Attribute Adapter (Generic)

Uses `AttributeInputAdapter` to handle any object exposing a text-like attribute, without writing adapter code at all.

#! src/hother/streamblocks_examples/03_adapters/11_attribute_adapter_generic.py

## Disable Original Events

Disables original event passthrough for a lightweight, extraction-only event stream with minimal overhead.

#! src/hother/streamblocks_examples/03_adapters/12_disable_original_events.py

## Manual Chunk Processing

Requires `GEMINI_API_KEY` (or `GOOGLE_API_KEY`). Processes chunks manually with `process_chunk()` instead of `process_stream()`, giving fine-grained control for custom buffering, multiple sources, or batch pipelines.

#! src/hother/streamblocks_examples/03_adapters/13_manual_chunk_processing.py

## Section Delta Events

Uses the section-specific delta events (`BlockHeaderDeltaEvent`, `BlockMetadataDeltaEvent`, `BlockContentDeltaEvent`) for type-safe handling of each block section as it streams.

#! src/hother/streamblocks_examples/03_adapters/14_section_delta_events.py

## Section End Events

Reacts to `BlockMetadataEndEvent` and `BlockContentEndEvent` to process completed sections early, before the block itself finishes, enabling early validation and resource release.

#! src/hother/streamblocks_examples/03_adapters/15_section_end_events.py

## Bidirectional Protocol

Combines input and output adapters in a `ProtocolStreamProcessor` for bidirectional protocol processing, with `EventCategory`-based filtering of what gets emitted.

#! src/hother/streamblocks_examples/03_adapters/16_bidirectional_protocol.py

## Custom Output Adapter

Writes a custom output adapter that converts StreamBlocks events into a simplified JSON event format, the pattern to follow when feeding events to a frontend or message bus.

#! src/hother/streamblocks_examples/03_adapters/17_custom_output_adapter.py
