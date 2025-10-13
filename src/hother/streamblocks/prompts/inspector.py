"""Content format inspection utilities for generating helpful prompts."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hother.streamblocks.core.types import BaseContent


def parse_block_docstring(block_class: type) -> tuple[str, str | None]:
    """Parse Block class docstring into description and usage.

    Extracts:
    - Description: First paragraph of docstring
    - Usage: Second paragraph or content after "Usage:" section

    Args:
        block_class: Block class to parse docstring from

    Returns:
        Tuple of (description, usage_info)
        usage_info is None if not present in docstring

    Example:
        >>> desc, usage = parse_block_docstring(FileOperations)
        >>> print(desc)
        Manage file creation, editing, and deletion operations
        >>> print(usage)
        Use this block when you need to create, edit, or delete files
    """
    docstring = inspect.getdoc(block_class)
    if not docstring:
        return "", None

    # Split into paragraphs (separated by blank lines)
    paragraphs: list[str] = []
    current_para: list[str] = []

    for line in docstring.split("\n"):
        stripped = line.strip()
        if not stripped:
            if current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []
        else:
            current_para.append(stripped)

    # Don't forget last paragraph
    if current_para:
        paragraphs.append(" ".join(current_para))

    if not paragraphs:
        return "", None

    # First paragraph is description
    description = paragraphs[0]

    # Look for "Usage:" section or use second paragraph
    usage_info: str | None = None

    for para in paragraphs[1:]:
        # Check if this paragraph starts with "Usage:"
        para_str: str = str(para)
        if para_str.lower().startswith("usage:") or para_str.lower().startswith("use this"):
            usage_info = para_str
            # Remove "Usage:" prefix if present
            if usage_info.lower().startswith("usage:"):
                usage_info = usage_info[6:].strip()
            break

    # If no explicit usage found, use second paragraph if it exists
    if usage_info is None and len(paragraphs) > 1:
        # Check if second paragraph looks like usage info
        second: str = str(paragraphs[1])
        if any(keyword in second.lower() for keyword in ["use this", "use when", "for"]):
            usage_info = second

    return description, usage_info


def inspect_content_format(content_class: type[BaseContent]) -> str | None:
    """Inspect content class to determine format description.

    This function intelligently determines how to describe the content format
    by checking multiple sources:

    1. Auto-generated description for @parse_as_json/@parse_as_yaml decorators
    2. Docstring from custom parse() method (if not the default BaseContent one)
    3. Returns None if no format information available

    Args:
        content_class: The content class to inspect

    Returns:
        Content format description string, or None if not available

    Example:
        >>> format_desc = inspect_content_format(FileOperationsContent)
        >>> print(format_desc)
        Parse file operations from raw text.

        Expected format:
        path/to/file.py:C
        ...
    """
    # Priority 1: Check for decorator markers FIRST
    # This handles @parse_as_json/@parse_as_yaml which inject parse methods
    format_type = _detect_decorator_type(content_class)
    if format_type:
        return _generate_decorator_format_description(content_class, format_type)

    # Priority 2: Custom parse method docstring (if not default)
    if hasattr(content_class, "parse"):
        parse_method = getattr(content_class, "parse")
        # Check if it's a classmethod or regular method
        func: Any
        if isinstance(parse_method, classmethod):
            # Get the underlying function
            func = parse_method.__func__
        else:
            # It might already be unwrapped
            func = parse_method

        docstring = inspect.getdoc(func)
        if docstring:
            # Skip the default BaseContent docstring
            if "Default parse method that just stores raw content" in docstring:
                return None

            # Extract just the description part (before Args/Returns sections)
            lines = docstring.split("\n")
            description_lines: list[str] = []
            for line in lines:
                # Stop at common docstring sections
                if line.strip().lower().startswith(("args:", "returns:", "raises:", "example:")):
                    break
                description_lines.append(line)

            description: str = "\n".join(description_lines).strip()
            if description:
                return description

    # Priority 3: No format information available
    return None


def _detect_decorator_type(content_class: type[BaseContent]) -> str | None:
    """Detect if content class was decorated with parse_as_json or parse_as_yaml.

    Args:
        content_class: Content class to check

    Returns:
        "json" if decorated with @parse_as_json,
        "yaml" if decorated with @parse_as_yaml,
        None otherwise
    """
    # Check if the parse method exists and was likely added by decorator
    if not hasattr(content_class, "parse"):
        return None

    # Try to get source code for source-based detection
    try:
        source = inspect.getsource(content_class)
        # Look for decorator usage in source
        if "@parse_as_json" in source:
            return "json"
        if "@parse_as_yaml" in source:
            return "yaml"
    except (OSError, TypeError):
        # Can't get source (dynamically created class) - use heuristic detection
        pass

    # For dynamically created classes, inspect the parse method itself
    parse_method = getattr(content_class, "parse")

    # Unwrap classmethod if needed
    func: Any
    if isinstance(parse_method, classmethod):
        func = parse_method.__func__
    else:
        func = parse_method

    # Check the method's code for JSON/YAML loading patterns
    try:
        import dis

        # Disassemble the function bytecode to look for module imports
        bytecode = dis.Bytecode(func)

        # Look for json or yaml module usage in the bytecode
        for instr in bytecode:
            if instr.opname in ("LOAD_GLOBAL", "LOAD_NAME"):
                if instr.argval in ("json", "loads"):
                    return "json"
                if instr.argval in ("yaml", "safe_load"):
                    return "yaml"
    except Exception:
        pass

    # Last resort: check function closure and defaults for hints
    try:
        func_code = func.__code__
        # Check variable names in the function
        if "json" in func_code.co_names or "loads" in func_code.co_names:
            return "json"
        if "yaml" in func_code.co_names or "safe_load" in func_code.co_names:
            return "yaml"
    except Exception:
        pass

    return None


def _generate_decorator_format_description(
    content_class: type[BaseContent],
    format_type: str,
) -> str:
    """Generate format description for decorated content classes.

    For classes decorated with @parse_as_json or @parse_as_yaml,
    generate a description showing the expected structure.

    Args:
        content_class: Content class to describe
        format_type: Either "json" or "yaml"

    Returns:
        Format description string
    """
    # Get the content fields (excluding raw_content which is from BaseContent)
    fields: list[tuple[str, Any]] = []
    if hasattr(content_class, "model_fields"):
        for field_name, field_info in content_class.model_fields.items():
            if field_name == "raw_content":
                continue
            fields.append((field_name, field_info))

    if not fields:
        return f"Content should be valid {format_type.upper()}"

    # Build format description
    lines = [f"Content should be valid {format_type.upper()} with the following structure:"]
    lines.append("")

    if format_type == "json":
        lines.append("{")
        for i, (field_name, field_info) in enumerate(fields):
            type_str = _format_type_hint(field_info.annotation)
            desc = field_info.description or ""
            comma = "," if i < len(fields) - 1 else ""
            if desc:
                lines.append(f'  "{field_name}": {type_str}{comma}  // {desc}')
            else:
                lines.append(f'  "{field_name}": {type_str}{comma}')
        lines.append("}")
    else:  # yaml
        for field_name, field_info in fields:
            type_str = _format_type_hint(field_info.annotation)
            desc = field_info.description or ""
            if desc:
                lines.append(f"{field_name}: {type_str}  # {desc}")
            else:
                lines.append(f"{field_name}: {type_str}")

    return "\n".join(lines)


def _format_type_hint(annotation: Any) -> str:
    """Format a type annotation as a readable string.

    Args:
        annotation: Type annotation to format

    Returns:
        Human-readable type string
    """
    if annotation is None:
        return "any"

    # Handle common types
    type_str = str(annotation)

    # Clean up the representation
    type_str = type_str.replace("typing.", "")
    type_str = type_str.replace("<class '", "").replace("'>", "")

    # Simplify common patterns
    if "str" in type_str:
        return '"string"'
    if "int" in type_str:
        return "123"
    if "float" in type_str:
        return "1.23"
    if "bool" in type_str:
        return "true/false"
    if "list" in type_str or "List" in type_str:
        return "[...]"
    if "dict" in type_str or "Dict" in type_str:
        return "{...}"

    return "..."
