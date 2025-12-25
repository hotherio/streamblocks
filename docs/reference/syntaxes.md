# Syntaxes

Block syntax definitions for parsing different formats.

## Built-in Syntaxes

### MarkdownFrontmatterSyntax

Parses blocks with YAML frontmatter between `---` delimiters:

```markdown
---
type: message
author: assistant
---
This is the message content.
```

```python
from hother.streamblocks.syntaxes import MarkdownFrontmatterSyntax

syntax = MarkdownFrontmatterSyntax()
```

### DelimiterFrontmatterSyntax

Parses blocks with custom delimiters:

```text
<<<BLOCK
type: code
language: python
>>>
def hello():
    print("Hello!")
<<<END>>>
```

```python
from hother.streamblocks.syntaxes import DelimiterFrontmatterSyntax

syntax = DelimiterFrontmatterSyntax(
    start_delimiter="<<<BLOCK",
    end_delimiter="<<<END>>>",
)
```

## Creating Custom Syntaxes

To create a custom syntax, extend `BaseSyntax`:

```python
from hother.streamblocks.syntaxes.base import BaseSyntax

class MySyntax(BaseSyntax):
    def detect_start(self, line: str) -> bool:
        return line.startswith("[[START]]")

    def detect_end(self, line: str) -> bool:
        return line.startswith("[[END]]")

    def parse_metadata(self, content: str) -> dict:
        return {"type": "custom"}
```

## API Reference

::: hother.streamblocks.syntaxes
    options:
      show_root_heading: true
      show_source: false
