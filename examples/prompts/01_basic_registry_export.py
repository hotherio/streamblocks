"""Basic example of exporting a registry to an LLM prompt.

This example demonstrates:
1. Creating a registry with a syntax
2. Registering block types
3. Generating a comprehensive prompt with examples
"""

from hother.streamblocks import DelimiterPreambleSyntax, Registry
from hother.streamblocks.blocks import FileOperations


def main() -> None:
    """Generate and display an LLM prompt from a registry."""
    # Create registry with delimiter preamble syntax
    registry = Registry(syntax=DelimiterPreambleSyntax())

    # Register block types with descriptions
    registry.register(
        "files_operations",
        FileOperations,
        description="Manage file creation, editing, and deletion operations",
    )

    # Generate comprehensive prompt with examples
    prompt = registry.to_prompt(include_examples=True)

    print("=" * 80)
    print("GENERATED LLM PROMPT")
    print("=" * 80)
    print(prompt)
    print("=" * 80)

    # Also demonstrate generating without examples
    print("\n\n")
    print("=" * 80)
    print("PROMPT WITHOUT EXAMPLES (Schema Only)")
    print("=" * 80)
    prompt_no_examples = registry.to_prompt(include_examples=False)
    print(prompt_no_examples)
    print("=" * 80)


if __name__ == "__main__":
    main()
