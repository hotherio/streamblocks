"""Generate LLM system prompts from a block registry.

Shows ``Registry.to_prompt()``, single-block ``generate_block_prompt()``, and a
custom prompt template. Everything runs offline -- no LLM calls -- because the
prompt is built purely from the block definitions (docstring, metadata fields,
content format, and examples).
"""

# --8<-- [start:imports]
from typing import ClassVar, Literal

from hother.streamblocks import (
    BaseContent,
    BaseMetadata,
    Block,
    DelimiterFrontmatterSyntax,
    Registry,
    generate_block_prompt,
    parse_as_yaml,
)

# --8<-- [end:imports]


# --8<-- [start:blocks]
class SearchMetadata(BaseMetadata):
    """Metadata for a catalog search block."""

    block_type: Literal["search"] = "search"


@parse_as_yaml()
class SearchContent(BaseContent):
    """Search parameters."""

    query: str = ""
    limit: int = 10


class Search(Block[SearchMetadata, SearchContent]):
    """Search the product catalog.

    Usage: emit a search block to look up products before answering.
    """

    # Declared examples are serialized into the prompt so the model sees a
    # concrete, correctly-formatted block.
    __examples__: ClassVar[list[dict[str, object]]] = [
        {
            "metadata": {"id": "s1", "block_type": "search"},
            "content": {"query": "wireless headphones", "limit": 5},
        },
    ]


# --8<-- [end:blocks]


def main() -> None:
    """Build prompts from a registry and print them."""
    # --8<-- [start:registry_prompt]
    registry = Registry(syntax=DelimiterFrontmatterSyntax())
    registry.register("search", Search)

    # A full system prompt documenting every registered block: the syntax
    # format, the block description + "Usage:" line, its metadata fields, the
    # YAML content format (from @parse_as_yaml), and serialized examples.
    prompt = registry.to_prompt()
    print(prompt)
    # --8<-- [end:registry_prompt]

    # --8<-- [start:single]
    # A prompt for a single block type -- here without the examples section.
    single = generate_block_prompt(Search, registry.syntax, include_examples=False)
    print(single)
    # --8<-- [end:single]

    # --8<-- [start:templates]
    # Register a custom template and select it with template_version. Templates
    # receive `syntax_name`, `syntax_format`, and `blocks` in their context.
    registry.register_template("compact", "Available blocks: {{ blocks | length }}", mode="registry")
    print(registry.to_prompt(template_version="compact"))
    # --8<-- [end:templates]


if __name__ == "__main__":
    main()
