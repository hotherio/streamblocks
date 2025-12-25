# Adapter Examples

These examples demonstrate stream adapters for different AI providers.

## Plain Text

### 01_identity_adapter_plain_text.py

Processing plain text streams without adaptation:

#! examples/03_adapters/01_identity_adapter_plain_text.py

## Provider Adapters

### 02_gemini_auto_detect.py

Gemini with automatic adapter detection:

!!! note "Requires API Key"
    Set `GEMINI_API_KEY` environment variable.

#! examples/03_adapters/02_gemini_auto_detect.py

### 03_openai_explicit_adapter.py

OpenAI with explicit adapter configuration:

!!! note "Requires API Key"
    Set `OPENAI_API_KEY` environment variable.

#! examples/03_adapters/03_openai_explicit_adapter.py

### 04_anthropic_adapter.py

Anthropic event stream handling:

!!! note "Requires API Key"
    Set `ANTHROPIC_API_KEY` environment variable.

#! examples/03_adapters/04_anthropic_adapter.py

## Event Handling

### 05_mixed_event_stream.py

Working with mixed event streams:

#! examples/03_adapters/05_mixed_event_stream.py

### 06_text_delta_streaming.py

Real-time text delta events:

#! examples/03_adapters/06_text_delta_streaming.py

### 07_block_opened_event.py

Detecting block opening:

#! examples/03_adapters/07_block_opened_event.py

## Configuration

### 08_configuration_flags.py

Processor configuration options:

#! examples/03_adapters/08_configuration_flags.py

## Custom Adapters

### 09_custom_adapter.py

Creating custom adapters:

#! examples/03_adapters/09_custom_adapter.py

### 10_callable_adapter.py

Using callable adapters:

#! examples/03_adapters/10_callable_adapter.py

### 11_attribute_adapter_generic.py

Generic attribute adapters:

#! examples/03_adapters/11_attribute_adapter_generic.py

## Advanced

### 12_disable_original_events.py

Controlling event emission:

#! examples/03_adapters/12_disable_original_events.py

### 13_manual_chunk_processing.py

Manual chunk processing:

!!! note "Requires API Key"
    Set `GEMINI_API_KEY` environment variable.

#! examples/03_adapters/13_manual_chunk_processing.py
