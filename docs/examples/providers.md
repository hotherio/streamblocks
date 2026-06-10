# Providers Examples

End-to-end demos against real AI providers. Both examples require a Gemini key — set `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) and install the extra with `pip install streamblocks[gemini]`. For adapter-level provider examples (OpenAI, Anthropic), see the [Adapters examples](adapters.md) and the [providers guide](../guides/providers.md).

## Gemini Simple Demo

Requires `GEMINI_API_KEY`. A simple end-to-end demo: one delimiter-frontmatter syntax for all block types, with Gemini generating blocks that are extracted live from the response stream.

#! src/hother/streamblocks_examples/07_providers/01_gemini_simple_demo.py

## Gemini Architect

Requires `GEMINI_API_KEY`. An AI software architect that mixes multiple block types in a single response — file operations, patches, tool calls, memory, and visualizations — showing how a realistic multi-block agent protocol comes together.

#! src/hother/streamblocks_examples/07_providers/02_gemini_architect.py

## Interactive UI examples (08_ui)

The `08_ui` category contains interactive examples that need a terminal to run, so they are not rendered here — run them locally instead:

- [`01_interactive_blocks.py`](https://github.com/hotherio/streamblocks/blob/main/src/hother/streamblocks_examples/08_ui/01_interactive_blocks.py) — demonstrates all interactive block types (choices, confirmations, forms) with CLI output.
- [`02_interactive_ui_demo.py`](https://github.com/hotherio/streamblocks/blob/main/src/hother/streamblocks_examples/08_ui/02_interactive_ui_demo.py) — a full [Textual](https://textual.textualize.io/) TUI that renders streaming blocks and lets you respond to them interactively.

```bash
uv run python src/hother/streamblocks_examples/08_ui/02_interactive_ui_demo.py
```
