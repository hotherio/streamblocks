# Syntaxes

A *syntax* defines the wire format of a block: how its opening is detected, where metadata lives, and what closes it. Each [`Registry`](blocks-and-registry.md) holds exactly one syntax instance. StreamBlocks ships three built-in syntaxes and lets you implement your own.

## DelimiterPreambleSyntax

The default. Metadata is inline in the opening line — compact and cheap for an LLM to emit:

```text
!!<id>:<type>[:param1:param2:...]
Content lines here
!!end
```

The opening delimiter carries the block `id` and `block_type` (both required, alphanumeric). Optional colon-separated parameters are stored in metadata as `param_0`, `param_1`, and so on:

```text
!!file123:operation:create:urgent
Create new config file
!!end
```

produces metadata `{"id": "file123", "block_type": "operation", "param_0": "create", "param_1": "urgent"}`.

| Option | Default | Description |
|--------|---------|-------------|
| `delimiter` | `"!!"` | Marker prefix for the opening line and the `!!end` closing line |

## DelimiterFrontmatterSyntax

Delimiter markers with a YAML frontmatter section for richer metadata:

```text
!!start
---
id: block_001
block_type: example
custom_field: value
---
Content lines here
!!end
```

The YAML between the `---` markers is parsed into your metadata model; it must include `id` and `block_type` when using `BaseMetadata`. Nested YAML (lists, mappings) is supported.

| Option | Default | Description |
|--------|---------|-------------|
| `start_delimiter` | `"!!start"` | Opening marker |
| `end_delimiter` | `"!!end"` | Closing marker |

```python
--8<-- "src/hother/streamblocks_examples/02_syntaxes/02_delimiter_frontmatter.py:setup"
```

## MarkdownFrontmatterSyntax

Markdown fenced code blocks with optional YAML frontmatter — useful when the stream is rendered as Markdown anyway:

````text
```[info_string]
---
id: block_001
block_type: example
custom_field: value
---
Content lines here
```
````

Both the info string and the frontmatter are optional. When frontmatter is absent (or has no `block_type`), the info string is used as the fallback `block_type` and all lines become content.

| Option | Default | Description |
|--------|---------|-------------|
| `fence` | `` "```" `` | Fence string |
| `info_string` | `None` | Restricts detection to fences with this info string; also the fallback `block_type` |

```python
--8<-- "src/hother/streamblocks_examples/02_syntaxes/01_markdown_frontmatter.py:setup"
```

## How a syntax is chosen

Pass either a `Syntax` enum member or a configured instance to the registry:

```python
from hother.streamblocks import Registry, DelimiterFrontmatterSyntax
from hother.streamblocks.syntaxes.models import Syntax

# Enum: built-in syntax with default options
registry = Registry(syntax=Syntax.DELIMITER_FRONTMATTER)

# Instance: full control over options
registry = Registry(syntax=DelimiterFrontmatterSyntax(start_delimiter="<<begin", end_delimiter="<<end"))
```

| Enum member | Syntax class |
|-------------|--------------|
| `Syntax.DELIMITER_PREAMBLE` (default) | `DelimiterPreambleSyntax` |
| `Syntax.DELIMITER_FRONTMATTER` | `DelimiterFrontmatterSyntax` |
| `Syntax.MARKDOWN_FRONTMATTER` | `MarkdownFrontmatterSyntax` |

Because a registry holds a single syntax, processing one stream with several wire formats requires separate processors or a custom syntax that recognizes multiple patterns.

## Custom syntaxes

Subclass `BaseSyntax` and implement four methods:

| Method | Role |
|--------|------|
| `detect_line(line, candidate)` | Return a `DetectionResult` flagging opening, closing, or metadata-boundary lines; accumulate lines into the candidate |
| `should_accumulate_metadata(candidate)` | Whether the candidate is still in its metadata section |
| `extract_block_type(candidate)` | Pull the `block_type` string out of a candidate so the registry can find the block class |
| `parse_block(candidate, block_class)` | Build the final `ParseResult` with parsed metadata and content |

A custom syntax plugs into the registry like any built-in one:

```python
--8<-- "src/hother/streamblocks_examples/02_syntaxes/04_custom_syntax.py:setup"
```

The full example implements an XML-comment wire format (`<!-- block:type id="..." -->` … `<!-- /block -->`) — see the [custom syntax example](../examples/syntaxes.md) for the complete `XMLBlockSyntax` implementation.

## Next steps

- [Blocks & Registry](blocks-and-registry.md) — how block classes attach to a syntax.
- [Events](events.md) — what the processor emits while a block accumulates.
- [Syntax examples](../examples/syntaxes.md) — runnable examples for every built-in syntax.
