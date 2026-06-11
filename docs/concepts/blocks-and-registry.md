# Blocks & Registry

A *block* is a typed unit of structured content extracted from a stream. The *registry* maps block type names to block classes and tells the processor which wire format to detect. This page covers the `Block` model, its metadata/content halves, and how the `Registry` ties everything together.

## The Block model

`Block[TMetadata, TContent]` is a Pydantic model with exactly two fields:

```python
class FileOperations(Block[FileOperationsMetadata, FileOperationsContent]):
    """File operations block."""
```

- `metadata: TMetadata`: parsed block metadata (from the header or frontmatter section).
- `content: TContent`: parsed block content (the body between the markers).

The generic parameters give you type-safe access: `block.metadata.description` and `block.content.operations` are fully typed. See [`blocks/agent/files.py`](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/blocks/agent/files.py) for the complete `FileOperations` definition used throughout the examples.

## Metadata: BaseMetadata

Every metadata model inherits from `BaseMetadata`, which requires two fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Block identifier, unique within the stream |
| `block_type` | `str` | Type name used to look up the block class in the registry |

Add your own fields on top:

```python
class FileOperationsMetadata(BaseMetadata):
    """Metadata for file operations blocks."""

    block_type: Literal["files_operations"] = "files_operations"
    description: str | None = None
```

## Content: BaseContent

Content models inherit from `BaseContent`, which has a single required field, `raw_content: str`: the original unparsed body text, always preserved. Parsing happens in the `parse()` classmethod:

```python
class BaseContent(BaseModel):
    raw_content: str

    @classmethod
    def parse(cls, raw_text: str) -> Self:
        return cls(raw_content=raw_text)
```

The default implementation just stores the raw text. Override `parse()` to turn the body into structured fields; see [Defining Custom Blocks](../guides/define-custom-blocks.md).

## Block vs ExtractedBlock

You *define* block types with `Block`; the processor *delivers* `ExtractedBlock` instances. `ExtractedBlock[TMetadata, TContent]` extends `Block` with extraction metadata:

| Field | Description |
|-------|-------------|
| `syntax_name` | Name of the syntax class that extracted the block |
| `raw_text` | Original raw text of the whole block, markers included |
| `line_start` / `line_end` | Line numbers in the stream |
| `hash_id` | Hash-based ID, useful for deduplication and caching |

`BlockEndEvent.get_block()` returns the typed `ExtractedBlock`:

```python
--8<-- "src/hother/streamblocks_examples/01_basics/01_basic_usage.py:events"
```

## The Registry

A `Registry` holds exactly one [syntax](syntaxes.md) and a mapping from block type names to block classes. All constructor arguments are keyword-only:

```python
registry = Registry(
    syntax=Syntax.DELIMITER_PREAMBLE,  # default
    blocks={"files_operations": FileOperations},  # optional bulk registration
    metadata_failure_mode=MetadataValidationFailureMode.ABORT_BLOCK,  # default
)
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `syntax` | `Syntax.DELIMITER_PREAMBLE` | A `Syntax` enum member or a `BaseSyntax` instance |
| `logger` | stdlib logger | Any object with `debug`/`info`/`warning`/`error`/`exception` methods |
| `blocks` | `None` | Dict of `block_type -> block_class` for bulk registration |
| `metadata_failure_mode` | `ABORT_BLOCK` | What to do when early metadata validation fails; see [Validation](../guides/validation.md) |

### Registering block types

`register()` maps a block type name to a class, optionally with validators:

```python
--8<-- "src/hother/streamblocks_examples/01_basics/01_basic_usage.py:register"
```

A validator is a callable that takes the `ExtractedBlock` and returns `bool`; a `False` result rejects the block with a `BlockErrorEvent`.

### Unregistered block types

You do not have to register anything. A block whose `block_type` has no registered class is still extracted, using plain `BaseMetadata` and `BaseContent`; metadata fields are parsed and the body lands in `raw_content`:

```python
--8<-- "src/hother/streamblocks_examples/01_basics/02_minimal_api.py:setup"
```

This minimal API is handy for prototyping before you commit to typed models. See the full example in [Basics examples](../examples/basics.md).

## Next steps

- [Syntaxes](syntaxes.md): the wire formats a registry can detect.
- [Defining Custom Blocks](../guides/define-custom-blocks.md): custom `parse()`, JSON/YAML decorators, structured output.
- [Validation](../guides/validation.md): registry validators and failure modes.
