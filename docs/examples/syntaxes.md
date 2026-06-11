# Syntaxes Examples

Examples covering the built-in block syntax formats and how to define your own. See the [Syntaxes concept page](../concepts/syntaxes.md) for background. All run offline with no API keys.

## Markdown Frontmatter

Extracts blocks written as Markdown code fences with YAML frontmatter using `MarkdownFrontmatterSyntax`, a natural fit for LLMs already fluent in Markdown.

#! src/hother/streamblocks_examples/02_syntaxes/01_markdown_frontmatter.py

## Delimiter Frontmatter

Uses `DelimiterFrontmatterSyntax`, the compact `!!id:type` ... `!!end` format with YAML frontmatter for metadata. This is the syntax used by most other examples.

#! src/hother/streamblocks_examples/02_syntaxes/02_delimiter_frontmatter.py

## Parsing Decorators

Shows the `@parse_as_yaml()` and `@parse_as_json()` decorators that automatically parse block content into structured Pydantic models, including STRICT vs PERMISSIVE error-handling strategies and graceful recovery from malformed content.

#! src/hother/streamblocks_examples/02_syntaxes/03_parsing_decorators.py

## Custom Syntax

Builds a completely custom syntax from scratch, defining your own open/close detection and section parsing, for when none of the built-in formats match your protocol.

#! src/hother/streamblocks_examples/02_syntaxes/04_custom_syntax.py
