"""Example of exporting a single block type to an LLM prompt.

This example demonstrates:
1. Exporting a single block without a registry
2. Using different syntaxes
3. Creating custom examples
"""

from hother.streamblocks import DelimiterPreambleSyntax, MarkdownFrontmatterSyntax
from hother.streamblocks.blocks import FileOperations


def main() -> None:
    """Generate and display prompts for a single block type."""
    # Export with default syntax
    print("=" * 80)
    print("FILE OPERATIONS BLOCK - Delimiter Preamble Syntax")
    print("=" * 80)
    prompt_delimiter = FileOperations.to_prompt()
    print(prompt_delimiter)
    print("=" * 80)

    # Export with markdown syntax
    print("\n\n")
    print("=" * 80)
    print("FILE OPERATIONS BLOCK - Markdown Frontmatter Syntax")
    print("=" * 80)
    prompt_markdown = FileOperations.to_prompt(syntax=MarkdownFrontmatterSyntax())
    print(prompt_markdown)
    print("=" * 80)

    # Show how many examples are defined
    print("\n\n")
    examples = FileOperations.get_examples()
    print(f"FileOperations has {len(examples)} examples defined")
    print("\nFirst example:")
    print(f"  ID: {examples[0].metadata.id}")
    print(f"  Description: {examples[0].metadata.description}")
    print(f"  Operations: {len(examples[0].content.operations)}")


if __name__ == "__main__":
    main()
