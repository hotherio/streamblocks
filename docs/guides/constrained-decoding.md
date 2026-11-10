# Constrained Decoding

A local model can be forced to produce only well-formed blocks. `Registry.to_grammar()` compiles the registry's syntax and block types into a grammar; a server that supports grammar-constrained decoding then only lets the model emit text the parser accepts.

## Generate the grammar

```python
--8<-- "src/hother/streamblocks_examples/01_basics/08_grammar_export.py:grammar"
```

The result is [GBNF](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md), the grammar format of llama.cpp and compatible servers such as LM Studio. How the grammar is passed depends on the server; check its documentation for the parameter name.

## What the grammar guarantees

| Part | Constraint |
|------|------------|
| Text around blocks | Any lines that cannot be mistaken for a block opening. Pass `allow_text=False` to allow blocks only. |
| Block type | One of the registered types |
| `id` | Letters, digits, underscores and dashes |
| Metadata fields | Required fields present, optional fields optional, in declaration order. Enumerations, integers, numbers and booleans are typed; strings are quoted. |
| Content | Any lines that are not a block marker, unless the content class defines its own grammar |
| Closing marker | Always present |

Fields the grammar cannot type (lists, nested objects) are left as free text, so they can still fail validation.

## Constrain the content

A content class can describe its own format by overriding `grammar()`. Build every line with the `line` factory it receives, so the block's own markers stay excluded. The built-in `PatchArtifact` does this for its search/replace hunks:

```python
from hother.streamblocks import BaseContent
from hother.streamblocks.grammar.nodes import Node, choice


class Answer(BaseContent):
    @classmethod
    def grammar(cls, line) -> Node:
        return choice("yes\n", "no\n")
```

## Supported syntaxes

| Syntax | Grammar export |
|--------|----------------|
| `DelimiterFrontmatterSyntax` | Yes |
| `XmlTagSyntax` | Yes |
| `DelimiterPreambleSyntax` | Yes, for blocks whose only metadata is positional parameters (`param_0`, ...) |
| `MarkdownFrontmatterSyntax` | Not yet |

A custom syntax opts in by overriding `BaseSyntax.grammar_rules()`.

## Check a grammar without a model

`hother.streamblocks.grammar.sample` draws random strings from a grammar. Feeding them to the processor verifies that everything the grammar allows is extracted cleanly:

```python
--8<-- "src/hother/streamblocks_examples/01_basics/08_grammar_export.py:round_trip"
```
