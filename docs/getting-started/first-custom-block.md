# Your First Custom Block

Built-in example blocks are fine for a demo, but the point of StreamBlocks is extracting *your* domain objects from a stream. This page defines a `task` block from scratch.

## Define metadata and content models

A block type is a `Block[TMetadata, TContent]` where the metadata model extends `BaseMetadata` and the content model extends `BaseContent`. Both are Pydantic models, so you get validation and typed access for free:

```python
--8<-- "src/hother/streamblocks_examples/00_quickstart/03_custom_block.py:models"
```

Two things to note:

- **Metadata** fields come from the block's metadata section (YAML frontmatter here). Defaults make fields optional in the stream.
- **Content** is produced by the `parse()` classmethod, which receives the raw text between the metadata section and the closing delimiter. `raw_content` always preserves the original text.

## Register and process

```python
--8<-- "src/hother/streamblocks_examples/00_quickstart/03_custom_block.py:example"
```

[View source on GitHub](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/00_quickstart/03_custom_block.py)

This example uses the **delimiter frontmatter** syntax: `!!start`, a YAML metadata section between `---` markers, free-form content, then `!!end`:

```text
!!start
---
id: task-1
block_type: task
title: Fix bug
priority: high
---
Fix the login issue
!!end
```

## Where to go from here

- Content that is JSON or YAML? Use the [`parse_as_json` / `parse_as_yaml` decorators](../guides/define-custom-blocks.md) instead of hand-writing `parse()`.
- Need to reject malformed blocks early? Add [validators](../guides/validation.md) to the registry.
- Curious how detection works under the hood? Read the [architecture overview](../concepts/index.md).
