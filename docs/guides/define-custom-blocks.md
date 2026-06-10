# Defining Custom Blocks

This guide shows three ways to turn raw block content into typed Python objects, from a hand-written `parse()` to fully schema-driven structured output.

## Define metadata and content models

A block type is three pieces: a metadata model (inherits `BaseMetadata`), a content model (inherits `BaseContent`), and the `Block` class binding them. Override the `parse()` classmethod on the content model to extract structure from the raw body — always keep `raw_content` populated with the original text:

```python
--8<-- "src/hother/streamblocks_examples/02_syntaxes/02_delimiter_frontmatter.py:models"
```

Register the block type and process as usual:

```python
--8<-- "src/hother/streamblocks_examples/02_syntaxes/02_delimiter_frontmatter.py:setup"
```

If `parse()` raises, the block is rejected with a `BlockErrorEvent` instead of a `BlockEndEvent` — see [Error Handling](error-handling.md).

## Parse JSON or YAML with decorators

When the block body *is* JSON or YAML, skip the boilerplate: the `@parse_as_json()` and `@parse_as_yaml()` decorators generate `parse()` for you. They load the text, then pass the resulting dict as keyword arguments to your content model.

```python
from hother.streamblocks import ParseStrategy, parse_as_json, parse_as_yaml
```

Both decorators take the same keyword-only arguments:

| Argument | Default | Description |
|----------|---------|-------------|
| `strategy` | `ParseStrategy.PERMISSIVE` | What to do when parsing or validation fails |
| `handle_non_dict` | `True` | Wrap non-dict values (scalars, lists) as `{"value": ...}` |

### PERMISSIVE: fall back to raw content

With `ParseStrategy.PERMISSIVE`, malformed input never rejects the block — the model is built with only `raw_content` set and your typed fields keep their defaults:

```python
--8<-- "src/hother/streamblocks_examples/02_syntaxes/03_parsing_decorators.py:yaml_permissive"
```

### STRICT: reject on parse errors

With `ParseStrategy.STRICT`, parse and validation errors propagate, so malformed content produces a `BlockErrorEvent` instead of a silently degraded block:

```python
--8<-- "src/hother/streamblocks_examples/02_syntaxes/03_parsing_decorators.py:json_strict"
```

Use STRICT when downstream code depends on the typed fields; use PERMISSIVE when you prefer to keep the raw text and recover manually.

### Non-dict content

JSON/YAML bodies are not always mappings. With `handle_non_dict=True` (the default) a scalar or list body is wrapped as `{"value": ...}`, so a `value` field on your model captures it. With `handle_non_dict=False`, non-dict input is discarded — only `raw_content` is set and typed fields keep their defaults:

```python
--8<-- "src/hother/streamblocks_examples/02_syntaxes/03_parsing_decorators.py:non_dict"
```

## Structured-output blocks from a schema

To validate block content against an arbitrary Pydantic schema (the streaming equivalent of structured output), generate the whole block type from the schema. The examples package ships a `create_structured_output_block` factory that builds metadata and content models around any `BaseModel`:

```python
--8<-- "src/hother/streamblocks_examples/01_basics/04_structured_output.py:schema"
```

```python
--8<-- "src/hother/streamblocks_examples/01_basics/04_structured_output.py:factory"
```

`strict=True` rejects blocks whose payload fails schema validation; `strict=False` falls back to `raw_content`. The factory also supports YAML payloads:

```python
--8<-- "src/hother/streamblocks_examples/01_basics/04_structured_output.py:yaml_factory"
```

The factory lives in the examples package ([`blocks/agent/structured_output.py`](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/blocks/agent/structured_output.py)), not the core library — copy it into your project and adapt it.

## Next steps

- [Validation](validation.md) — add business-rule validators on top of parsing.
- [Blocks & Registry](../concepts/blocks-and-registry.md) — the `Block` model in depth.
- [Block examples](../examples/blocks.md) — ready-made block types to copy.
