# API Reference

Everything importable from `hother.streamblocks`, grouped by area. All names below are re-exported at the package root:

```python
from hother.streamblocks import Registry, StreamBlockProcessor, BlockEndEvent
```

## Processors

[Processors](processors.md)

- `StreamBlockProcessor`: single-syntax stream processor (the common case)
- `ProtocolStreamProcessor`: protocol-event processor with output adaptation
- `ProcessorConfig`: event-volume and safety-limit configuration
- `StreamState`: processor stream state

## Registry & Models

[Registry & Models](registry-and-models.md)

- `Registry`: maps block types to block classes; owns the syntax. `to_prompt()`, `register_template()`, `serialize_block()`, and `registered_blocks` support prompt generation
- `Block[TMetadata, TContent]`: user-facing generic block base; `__examples__` + `get_examples()` feed prompts
- `ExtractedBlock`: runtime block with extraction metadata
- `BlockCandidate`: in-flight block accumulation
- `BaseMetadata`, `BaseContent`: base Pydantic models for block typing

## Prompts

[Prompts](prompts.md)

- `generate_block_prompt`: build an instruction prompt for a single block type
- `TemplateManager`: Jinja2 template management for prompt A/B versioning
- See also `Registry.to_prompt()` and the [Generating Prompts](../guides/generate-prompts.md) guide

## Events

[Events](events.md)

- `Event`: discriminated union of all event types
- `EventType`, `BlockState`, `BlockErrorCode`: enums
- Lifecycle: `StreamStartedEvent`, `StreamFinishedEvent`, `StreamErrorEvent`
- Text: `TextContentEvent`, `TextDeltaEvent`
- Block: `BlockStartEvent`, `BlockHeaderDeltaEvent`, `BlockMetadataDeltaEvent`, `BlockContentDeltaEvent`, `BlockMetadataEndEvent`, `BlockContentEndEvent`, `BlockEndEvent`, `BlockErrorEvent`
- `CustomEvent`, `BaseEvent`

## Syntaxes

[Syntaxes](syntaxes.md)

- `DelimiterPreambleSyntax`, `DelimiterFrontmatterSyntax`, `MarkdownFrontmatterSyntax`
- `BaseSyntax`: base class for custom syntaxes
- `Syntax`: enum for factory-based selection
- `DetectionResult`, `ParseResult`

## Adapters

[Adapters](adapters.md)

- `InputProtocolAdapter`, `OutputProtocolAdapter`, `BidirectionalAdapter`: protocols
- `InputAdapterRegistry`, `detect_input_adapter`: auto-detection
- `EventCategory`: input event categorization

## Parsing & Validation

[Parsing & Validation](parsing-and-validation.md)

- `parse_as_json`, `parse_as_yaml`, `ParseStrategy`: content parsing decorators
- `ValidationResult`, `MetadataValidationFailureMode`: validation types

## Extensions

[Extensions](extensions.md)

- `hother.streamblocks.extensions.gemini` / `.openai` / `.anthropic`: provider input adapters
- `hother.streamblocks.extensions.agui`: bidirectional AG-UI adapters and filters

## Integrations

[Integrations](integrations.md)

- `hother.streamblocks.integrations.pydantic_ai`: `BlockAwareAgent`, `AgentStreamProcessor`
