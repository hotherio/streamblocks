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

## Next steps

- [Error Handling](error-handling.md): react to `BlockErrorEvent` and its error codes.
- [Defining Custom Blocks](define-custom-blocks.md): parsing, the stage before validation.
- [Events](../concepts/events.md): `BlockMetadataEndEvent` and `BlockContentEndEvent` carry the validation outcome.
