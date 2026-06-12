# Quickstart Examples

Three ultra-minimal examples to get a feel for StreamBlocks in a few minutes. Each runs offline against a simulated stream; no API keys required. Continue with the [basics examples](basics.md) afterwards.

## Hello World

The simplest working example: register a block type, process a text stream, and react to `BlockEndEvent` when a complete block is extracted.

#! src/hother/streamblocks_examples/00_quickstart/01_hello_world.py

## Basic Stream

Processes text arriving in chunks, distinguishing extracted blocks from surrounding free text via `TextContentEvent`. This is the core streaming loop you will use everywhere.

#! src/hother/streamblocks_examples/00_quickstart/02_basic_stream.py

## Custom Block

Defines a custom block type with its own metadata and content models, then extracts it with `DelimiterFrontmatterSyntax`. The key takeaway: a block is just a pair of Pydantic models registered under a type name.

#! src/hother/streamblocks_examples/00_quickstart/03_custom_block.py
