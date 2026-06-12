# Generating Prompts

For a model to emit blocks your registry can parse, it needs to know the block format. Rather than hand-writing that prompt, `Registry.to_prompt()` builds it from your block definitions — the docstring, metadata fields, content format, and examples. The *same* registry then parses the model's output, so the instructions and the parser never drift apart. See [Blocks & Registry](../concepts/blocks-and-registry.md#the-block-round-trip) for the round-trip idea.

## Make your blocks self-describing

Prompt quality comes straight from your block definitions. Three things feed the prompt:

- the **block docstring**: the first paragraph is the description; a paragraph starting with `Usage:` becomes the usage guidance (this is the only convention — implicit phrasing is not detected).
- the **content format**: `@parse_as_json` / `@parse_as_yaml` mark the body format, rendered as a JSON/YAML structure hint built from the content model's fields and their `Field(description=...)`.
- **examples**: `__examples__` entries are serialized in the registry's syntax and shown verbatim.

```python
--8<-- "src/hother/streamblocks_examples/01_basics/07_prompt_generation.py:imports"
```

```python
--8<-- "src/hother/streamblocks_examples/01_basics/07_prompt_generation.py:blocks"
```

## Generate a registry prompt

`Registry.to_prompt()` documents every registered block in the registry's syntax:

```python
--8<-- "src/hother/streamblocks_examples/01_basics/07_prompt_generation.py:registry_prompt"
```

Pass `include_examples=False` to omit the examples section. Because the prompt is built from the registry's own syntax, switching syntaxes (for example `MarkdownFrontmatterSyntax`) changes the format shown to the model automatically.

## Document a single block

For one block type, call `generate_block_prompt(block_class, syntax, ...)`:

```python
--8<-- "src/hother/streamblocks_examples/01_basics/07_prompt_generation.py:single"
```

## Customize the template

Prompts render through Jinja2 templates. Register a custom template and select it with `template_version`; the template context exposes `syntax_name`, `syntax_format`, and `blocks`:

```python
--8<-- "src/hother/streamblocks_examples/01_basics/07_prompt_generation.py:templates"
```

This is handy for A/B testing prompt phrasings without touching block definitions.

## Serialize blocks back to text

`Registry.serialize_block()` (and each syntax's `serialize_block()`) renders a `Block` instance into its wire format — the same mechanism used to render `__examples__`. It is the inverse of parsing, useful for few-shot examples or round-trip tests. `BaseSyntax.describe_format()` returns the human-readable format description embedded in the prompt.

## Next steps

- [Pydantic AI](pydantic-ai.md): feed the generated prompt to an agent, then extract blocks from its stream.
- [Defining Custom Blocks](define-custom-blocks.md): the block models the prompt is built from.
- [Prompts reference](../reference/prompts.md): the full API.
