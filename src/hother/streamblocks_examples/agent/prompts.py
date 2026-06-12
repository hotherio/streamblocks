"""System prompt builder for the ReAct agent.

Generates prompts that instruct the LLM to emit ToolCall and FinalAnswer
blocks in the correct format for StreamBlocks parsing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hother.streamblocks.core.registry import Registry
    from hother.streamblocks_examples.agent.executor import ToolDefinition

# Preamble: General instructions and rules (no placeholders)
PREAMBLE = """You are an AI assistant that can use tools to help answer questions.

## Response Format

IMPORTANT: Every block MUST start with !!start and end with !!end. Blocks without !!end are rejected!

## Important Rules

1. CRITICAL: Every block MUST end with !!end on its own line. A block without !!end will be REJECTED and you will need to retry.
2. You can emit multiple tool_call blocks in a single response - as soon as a block is properly closed (!!end) it will be executed in the background.
3. When a tool_call block is finished to be executed, you will receive the tool result
4. When you are done with your task, use a final_answer block
5. Always use the exact block format shown below
6. Parameters must be valid YAML
7. Do not ask anything to the user - you do not have tool for this.
8. Use a wait block when you need results from specific tools before continuing (e.g., search before order)."""


def build_blocks_section(registry: Registry) -> str:
    """Extract block documentation from registry.

    Iterates through registered block classes and extracts their
    __doc_example__ attributes if present.

    Args:
        registry: The StreamBlocks registry containing registered block classes

    Returns:
        Combined documentation for all blocks, separated by newlines
    """
    blocks_docs = []
    for block_type in sorted(registry._block_classes.keys()):
        block_class = registry._block_classes[block_type]
        if hasattr(block_class, "__doc_example__"):
            blocks_docs.append(block_class.__doc_example__)
    return "\n\n".join(blocks_docs)


def format_tool_description(tool: ToolDefinition) -> str:
    """Format a single tool for the system prompt.

    Includes JSON schemas for Pydantic models so the LLM knows
    the exact structure of nested objects.
    """
    lines = [f"### {tool.name}"]
    if tool.description:
        lines.append(tool.description)
    lines.append("")
    lines.append("Parameters:")
    if tool.params_schema:
        for param_name, param_info in tool.params_schema.items():
            required = "(required)" if param_info.get("required", True) else "(optional)"
            param_type = param_info.get("type", "any")
            lines.append(f"  - {param_name}: {param_type} {required}")

            # Include JSON schema for Pydantic models
            model_class = param_info.get("model_class")
            if model_class and hasattr(model_class, "model_json_schema"):
                schema = model_class.model_json_schema()
                # Extract just the properties for readability
                props = schema.get("properties", {})
                req_fields = schema.get("required", [])
                is_list = param_info.get("is_list", False)

                if props:
                    prefix = "    (list of objects" if is_list else "    (object"
                    lines.append(f"{prefix} with fields:")
                    for field_name, field_info in props.items():
                        field_type = field_info.get("type", "any")
                        field_req = "required" if field_name in req_fields else "optional"
                        default = field_info.get("default")
                        default_str = f", default={default}" if default is not None else ""

                        # Extract enum values if present (from Literal types)
                        enum_values = field_info.get("enum")
                        if enum_values:
                            field_type = f"one of: {enum_values}"

                        lines.append(f"      - {field_name}: {field_type} ({field_req}{default_str})")

                        # Extract description if present (from Field(description=...))
                        description = field_info.get("description")
                        if description:
                            lines.append(f"        {description}")
                    lines.append("    )")
    else:
        lines.append("  (none)")
    return "\n".join(lines)


def build_system_prompt(tools: list[ToolDefinition], registry: Registry) -> str:
    """Build the complete system prompt as concatenated sections.

    Per Gemini API docs (https://googleapis.github.io/python-genai/):
    - system_instruction is passed as a single string
    - We structure it clearly by concatenating distinct sections

    Args:
        tools: List of tool definitions to include
        registry: StreamBlocks registry containing block classes with __doc_example__

    Returns:
        Complete system prompt string (no template placeholders)
    """
    # Part 1: Preamble
    parts = [PREAMBLE]

    # Part 2: Block documentation (extracted from registry)
    blocks_section = build_blocks_section(registry)
    parts.append("## Available Blocks\n\n" + blocks_section)

    # Part 3: Tool descriptions
    tools_section = "\n\n".join(format_tool_description(tool) for tool in tools) if tools else "(No tools available)"
    parts.append("## Available Tools\n\n" + tools_section)

    # Concatenate with clear separators (no .format() templating)
    return "\n\n---\n\n".join(parts)


def format_tool_result(tool_name: str, result: str, success: bool = True) -> str:
    """Format a tool result as a message to the LLM.

    Args:
        tool_name: Name of the tool that was called
        result: Result or error message
        success: Whether the tool succeeded

    Returns:
        Formatted tool result string
    """
    if success:
        return f"Tool result from {tool_name}:\n{result}"
    return f"Error from {tool_name}:\n{result}"
