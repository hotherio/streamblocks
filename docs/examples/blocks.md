# Blocks Examples

Examples of concrete, ready-to-use block types for agent-style workflows. They build on the reusable block library shipped with the examples at [`src/hother/streamblocks_examples/blocks/`](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/blocks), which provides file operations, patches, tool calls, memory, visualization, and interactive block definitions you can import directly. All examples run offline with no API keys. To define your own block types, see the [Defining Custom Blocks guide](../guides/define-custom-blocks.md).

## Artifact Blocks

The built-in artifact blocks shipped with the library (`hother.streamblocks.blocks.artifacts`): `FileArtifact`, `PatchArtifact` and `DocumentArtifact`, here with `XmlTagSyntax`. A file and a search/replace patch are extracted from prose as they stream and applied to an in-memory project.

#! src/hother/streamblocks_examples/04_blocks/06_artifact_blocks.py

## Guarded Generation

Stream validators reject an artifact from its opening line (a file outside the allowed directories) and stop the stream, so a model does not keep generating output that will be discarded.

#! src/hother/streamblocks_examples/04_blocks/07_guarded_generation.py

## Patch Content

A deep dive into `PatchContent` with various patch formats (unified diff, search/replace, ...), showing how patch blocks are parsed and applied.

#! src/hother/streamblocks_examples/04_blocks/01_patch_content.py

## Patch Block

The minimal usage of the reusable `Patch` block for streaming code diffs and modifications.

#! src/hother/streamblocks_examples/04_blocks/02_patch_block.py

## ToolCall Block

The `ToolCall` block for invoking external tools with structured parameters, the StreamBlocks-native way to express tool use in a text stream.

#! src/hother/streamblocks_examples/04_blocks/03_toolcall_block.py

## Memory Block

The `Memory` block for context storage and recall operations, letting an agent persist and retrieve information mid-stream.

#! src/hother/streamblocks_examples/04_blocks/04_memory_block.py

## Visualization Block

The `Visualization` block for charts, diagrams, and tables, structured visual payloads a frontend can render as they complete.

#! src/hother/streamblocks_examples/04_blocks/05_visualization_block.py
