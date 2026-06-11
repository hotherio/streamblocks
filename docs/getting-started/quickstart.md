# Quickstart

This page walks you through extracting your first structured block from a text stream.

## The idea

LLMs are good at emitting structured blocks inside free-form text when you ask them to. StreamBlocks detects those blocks *while the text streams* and hands you typed, validated Python objects, without waiting for the stream to finish.

A block in the default delimiter syntax looks like this:

```text
!!block01:files_operations
src/main.py:C
!!end
```

The opening line carries the block `id` (`block01`) and `block_type` (`files_operations`); everything until `!!end` is the block content.

## Hello, block

Three steps: create a [`Registry`](../concepts/blocks-and-registry.md), register a block class for each `block_type` you expect, and feed any async text stream to the processor.

```python
--8<-- "src/hother/streamblocks_examples/00_quickstart/01_hello_world.py:imports"

--8<-- "src/hother/streamblocks_examples/00_quickstart/01_hello_world.py:example"
```

[View source on GitHub](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/00_quickstart/01_hello_world.py)

The processor emits an [event](../concepts/events.md) for everything it sees. Here we only react to `BlockEndEvent`, emitted when a block closes successfully, and `event.get_block()` returns the parsed block with typed `metadata` and `content`.

## Mixing text and blocks

Real streams interleave prose and blocks. Text outside blocks is emitted as `TextContentEvent`, so nothing is lost:

```python
--8<-- "src/hother/streamblocks_examples/00_quickstart/02_basic_stream.py:example"
```

[View source on GitHub](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/00_quickstart/02_basic_stream.py)

## What just happened?

1. `Registry()` defaults to the [delimiter preamble syntax](../concepts/syntaxes.md) (`!!<id>:<type>` … `!!end`).
2. `registry.register("files_operations", FileOperations)` maps the block type string to a `Block` class with typed metadata and content models.
3. `processor.process_stream(stream)` consumes any `AsyncIterator[str]` and yields events as lines complete.
4. When the closing delimiter arrives, the block's content is parsed and validated, then `BlockEndEvent` delivers it.

## Next steps

- [Your First Custom Block](first-custom-block.md): define your own metadata and content models.
- [Events](../concepts/events.md): the full event model, including per-section streaming deltas.
- [Providers guide](../guides/providers.md): plug in OpenAI, Anthropic, or Gemini streams instead of the simulator.
