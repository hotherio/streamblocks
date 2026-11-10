# Validation

Parsing guarantees structure; validators enforce your rules on top of it. The registry supports three validator kinds, each running at a different point in the block lifecycle.

## Three validation stages

| Stage | Registered with | Signature | Runs when |
|-------|-----------------|-----------|-----------|
| Metadata | `registry.add_metadata_validator(block_type, fn)` | `(raw: str, parsed: dict \| None) -> ValidationResult` | Metadata section completes, *before* content accumulates |
| Content | `registry.add_content_validator(block_type, fn)` | `(raw: str, parsed: dict \| None) -> ValidationResult` | Content section completes, before the final `BlockEndEvent` |
| Block | `registry.add_validator(block_type, fn)` or `register(..., validators=[fn])` | `(block: ExtractedBlock) -> bool` | After the full block is parsed |

Validators of each kind run in registration order; the first failure stops the chain.

## Early metadata validation

Metadata validators receive the raw metadata string and the parsed dict (or `None` if parsing failed) and return a `ValidationResult`:

```python
--8<-- "src/hother/streamblocks_examples/01_basics/05_metadata_validators.py:validators"
```

`ValidationResult` is a small dataclass with two constructors:

```python
ValidationResult.success()
ValidationResult.failure("ID must start with 'ops-'")
```

Because metadata validators fire at the *end of the metadata section*, you can reject a block before its content streams in, useful for skipping large payloads you already know you don't want.

## Failure modes

What happens after a metadata validation failure is controlled by the registry's `metadata_failure_mode`:

| Mode | Behavior |
|------|----------|
| `MetadataValidationFailureMode.ABORT_BLOCK` (default) | Emit a `BlockErrorEvent` immediately and stop processing the block |
| `MetadataValidationFailureMode.CONTINUE` | Log a warning and keep processing content normally |
| `MetadataValidationFailureMode.SKIP_CONTENT` | Skip content accumulation and emit a partial block |

```python
--8<-- "src/hother/streamblocks_examples/01_basics/05_metadata_validators.py:abort_mode"
```

## Content and block validators

Content validators mirror metadata validators but run on the raw content when the content section ends. Block validators are plain predicates over the final `ExtractedBlock`; returning `False` rejects the block with a `BlockErrorEvent` (`VALIDATION_FAILED`).

## Composing validators

All three kinds combine on a single block type:

```python
--8<-- "src/hother/streamblocks_examples/01_basics/06_validator_composition.py:metadata_validators"
```

```python
--8<-- "src/hother/streamblocks_examples/01_basics/06_validator_composition.py:general_validators"
```

```python
--8<-- "src/hother/streamblocks_examples/01_basics/06_validator_composition.py:register_validators"
```

A block must pass every registered validator to be delivered through `BlockEndEvent`.

## Validating while the block streams

The validators above run when a section or a block is complete. A *stream validator* runs on every line of a block, starting with its opening line, and can reject the block before the rest of it is written. It receives a `PartialBlock`: the block type and metadata once they are known, the section, the latest line, and the lines so far.

```python
--8<-- "src/hother/streamblocks_examples/04_blocks/07_guarded_generation.py:setup"
```

A rejected block is dropped with a `BlockErrorEvent` whose code is `ABORTED`. What happens next depends on `ProcessorConfig.abort_stream_on_failure`:

| `abort_stream_on_failure` | After a rejection |
|---------------------------|-------------------|
| `False` (default) | Processing continues. The remaining lines of the rejected block are emitted as plain text, and later blocks are extracted normally. |
| `True` | The processor ignores the rest of the stream, `processor.aborted` becomes `True`, and `process_stream` closes the upstream iterator. With a model stream this ends generation, so the rest of the output is neither produced nor paid for. |

```python
--8<-- "src/hother/streamblocks_examples/04_blocks/07_guarded_generation.py:process"
```

When the metadata becomes available depends on the syntax: on the opening line for `XmlTagSyntax` and `DelimiterPreambleSyntax`, at the end of the frontmatter for the frontmatter syntaxes. Pass a block type as the second argument of `add_stream_validator` to run a validator for that type only.

`hother.streamblocks.guards` ships ready-made stream validators:

| Guard | Rejects a block when |
|-------|----------------------|
| `path_within(*roots, field="path")` | its path metadata is absolute, escapes the project, or is outside the allowed directories |
| `max_lines(limit)` | its content has more than `limit` lines |
| `max_size(limit)` | it is larger than `limit` characters |
| `forbid_patterns(*patterns)` | a content line matches one of the regular expressions |

## Next steps

- [Error Handling](error-handling.md): react to `BlockErrorEvent` and its error codes.
- [Defining Custom Blocks](define-custom-blocks.md): parsing, the stage before validation.
- [Events](../concepts/events.md): `BlockMetadataEndEvent` and `BlockContentEndEvent` carry the validation outcome.
