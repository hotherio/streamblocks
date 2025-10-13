"""Prompt generation utilities for StreamBlocks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from hother.streamblocks.prompts.inspector import inspect_content_format, parse_block_docstring
from hother.streamblocks.prompts.manager import TemplateManager

if TYPE_CHECKING:
    from hother.streamblocks.core.models import Block
    from hother.streamblocks.syntaxes.base import BaseSyntax


def generate_block_prompt(
    block_class: type[Block],
    syntax: BaseSyntax,
    include_examples: bool = True,
    template_version: str = "default",
    description: str = "",
) -> str:
    """Generate LLM instruction prompt for a single block type.

    Args:
        block_class: The block class to generate prompt for
        syntax: Syntax instance to use for serialization
        include_examples: Whether to include examples from __examples__
        template_version: Template version for A/B testing
        description: Optional custom description (overrides docstring)

    Returns:
        String prompt for this block type

    Example:
        >>> from hother.streamblocks import DelimiterPreambleSyntax
        >>> from hother.streamblocks.blocks import FileOperations
        >>> syntax = DelimiterPreambleSyntax()
        >>> prompt = generate_block_prompt(FileOperations, syntax)
        >>> print(prompt)
    """
    # Parse Block docstring for description and usage
    block_desc, block_usage = parse_block_docstring(block_class)

    # Extract content class for format inspection
    content_class = _extract_content_class(block_class)

    # Inspect content format
    content_format = inspect_content_format(content_class) if content_class else None

    # Build context for template
    context = {
        "syntax_name": syntax.__class__.__name__,
        "syntax_format": syntax.describe_format(),
        "block": {
            "name": _infer_block_type_name(block_class),
            "description": description or block_desc,
            "usage": block_usage,
            "content_format": content_format,
            "metadata_schema": _extract_schema(block_class, "metadata"),
            "content_schema": _extract_schema(block_class, "content"),
            "examples": [],
        },
    }

    # Get examples from __examples__ and serialize them
    if include_examples:
        examples = block_class.get_examples()
        for example in examples:
            serialized = syntax.serialize_block(example)
            context["block"]["examples"].append(serialized)

    # Render template
    manager = TemplateManager()
    return manager.render(context, template_version, mode="single")


def _extract_content_class(block_class: type) -> type | None:
    """Extract content class from block class.

    Args:
        block_class: Block class to extract from

    Returns:
        Content class or None if not found
    """
    if hasattr(block_class, "model_fields"):
        content_field = block_class.model_fields.get("content")
        if content_field and content_field.annotation:
            return content_field.annotation
    return None


def _infer_block_type_name(block_class: type) -> str:
    """Infer block type name from class.

    Tries to extract from a sample metadata instance, falls back to snake_case conversion.

    Args:
        block_class: Block class to infer name from

    Returns:
        Block type name as string
    """
    # Try to get from a sample metadata instance
    if hasattr(block_class, "model_fields"):
        metadata_field = block_class.model_fields.get("metadata")
        if metadata_field and metadata_field.annotation:
            try:
                # Try to get block_type from annotation
                sample = metadata_field.annotation.model_construct()
                if hasattr(sample, "block_type"):
                    return sample.block_type
            except Exception:
                pass

    # Fallback to snake_case of class name
    name = block_class.__name__
    # Simple camelCase to snake_case conversion
    result = []
    for i, char in enumerate(name):
        if char.isupper() and i > 0:
            result.append("_")
        result.append(char.lower())
    return "".join(result)


def _extract_schema(
    block_class: type,
    field_name: str,
) -> dict[str, Any]:
    """Extract JSON schema from Pydantic field with field filtering.

    This function extracts the schema and filters out common/internal fields
    that don't need to be shown in prompts.

    Args:
        block_class: Block class to extract schema from
        field_name: Field name ("metadata" or "content")

    Returns:
        Filtered JSON schema dictionary with only user-facing fields
    """
    if not hasattr(block_class, "model_fields"):
        return {}

    field = block_class.model_fields.get(field_name)
    if not field or not field.annotation:
        return {}

    try:
        full_schema = field.annotation.model_json_schema()
    except Exception:
        return {}

    # Apply field filtering
    return _filter_schema_fields(full_schema, field_name)


def _filter_schema_fields(
    schema: dict[str, Any],
    field_type: str,
) -> dict[str, Any]:
    """Filter out common and internal fields from schema.

    Always excludes:
    - Metadata: id, block_type
    - Content: raw_content, operations (parsed fields)

    Args:
        schema: Full JSON schema
        field_type: "metadata" or "content"

    Returns:
        Filtered schema
    """
    # Default exclusions based on field type
    if field_type == "metadata":
        exclude_fields = {"id", "block_type"}
    elif field_type == "content":
        # Exclude internal/parsed fields
        exclude_fields = {"raw_content", "operations", "parameters", "diff"}
    else:
        exclude_fields = set()

    # Filter the schema
    if "properties" not in schema:
        return schema

    filtered_properties = {
        key: value
        for key, value in schema["properties"].items()
        if key not in exclude_fields
    }

    # Update the schema with filtered properties
    filtered_schema = schema.copy()
    filtered_schema["properties"] = filtered_properties

    # Update required fields list if present
    if "required" in filtered_schema:
        filtered_schema["required"] = [
            field for field in filtered_schema["required"] if field not in exclude_fields
        ]

    return filtered_schema
