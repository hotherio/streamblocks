"""Shared utilities for MkDocs hooks."""

import re
from pathlib import Path

# GitHub repository configuration
GITHUB_REPO = "hotherio/streamblocks"
GITHUB_BRANCH = "main"


def get_github_link(file_path: str, start_line: int | None = None, end_line: int | None = None) -> str:
    """Generate a GitHub link to a file or specific lines.

    Args:
        file_path: Relative path from repository root
        start_line: Optional starting line number
        end_line: Optional ending line number

    Returns:
        Full GitHub URL to the file or line range
    """
    base_url = f"https://github.com/{GITHUB_REPO}/tree/{GITHUB_BRANCH}/{file_path}"

    if start_line is not None:
        if end_line is not None and end_line != start_line:
            return f"{base_url}#L{start_line}-L{end_line}"
        return f"{base_url}#L{start_line}"

    return base_url


def strip_leading_docstring(code: str) -> str:
    """Remove leading module docstring from Python code.

    Args:
        code: Python source code

    Returns:
        Code with leading docstring removed
    """
    # Match triple-quoted strings at the start (with optional shebang/encoding)
    pattern = r'^(#!.*?\n)?(# -\*- coding:.*?\n)?(\s*"""[\s\S]*?"""\s*\n|\s*\'\'\'[\s\S]*?\'\'\'\s*\n)?'
    return re.sub(pattern, r"\1\2", code, count=1)


def format_code_block(
    code: str,
    file_path: str,
    language: str = "python",
    start_line: int | None = None,
    end_line: int | None = None,
    title: str | None = None,
) -> str:
    """Format code into a markdown code block with metadata.

    Args:
        code: The code content
        file_path: Path to the source file
        language: Programming language for syntax highlighting
        start_line: Optional starting line number
        end_line: Optional ending line number
        title: Optional custom title (defaults to file_path)

    Returns:
        Formatted markdown code block with GitHub link
    """
    block_title = title or file_path
    github_link = get_github_link(file_path, start_line, end_line)

    # Build code block
    result = f'```{language} title="{block_title}"\n{code}\n```\n'

    # Add source link
    if start_line and end_line:
        result += f"_[View source on GitHub (lines {start_line}-{end_line})]({github_link})_"
    else:
        result += f"_[View source on GitHub]({github_link})_"

    return result


def resolve_file_path(path: str, base_dir: Path | None = None) -> Path | None:
    """Resolve a file path relative to base directory or repository root.

    Args:
        path: File path (relative or absolute)
        base_dir: Optional base directory (defaults to repository root)

    Returns:
        Resolved Path object, or None if file doesn't exist
    """
    if base_dir is None:
        # Default to repository root (3 levels up from docs/.hooks/)
        base_dir = Path(__file__).parent.parent.parent

    file_path = Path(path)

    # If absolute path, use as-is
    if file_path.is_absolute():
        return file_path if file_path.exists() else None

    # Try relative to base_dir
    resolved = base_dir / file_path
    if resolved.exists():
        return resolved

    # Try relative to current working directory
    if file_path.exists():
        return file_path

    return None
