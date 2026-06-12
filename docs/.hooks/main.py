"""MkDocs lifecycle hooks for Streamblocks documentation.

This module provides hooks that run during MkDocs build process to:
- Inject example code files
- Generate tabbed package manager commands
"""

import os
import re
import sys
from pathlib import Path

from mkdocs.config import Config
from mkdocs.exceptions import PluginError
from mkdocs.structure.files import Files
from mkdocs.structure.pages import Page

# Add hooks directory to path for imports
_hooks_dir = Path(__file__).parent
if str(_hooks_dir) not in sys.path:
    sys.path.insert(0, str(_hooks_dir))

# Now import from sibling modules
import utils

# Escape hatch for live editing (mkdocs serve): render an error admonition
# instead of aborting the build when an example file is missing.
LENIENT_ENV_VAR = "STREAMBLOCKS_DOCS_LENIENT"
LENIENT_ENABLED = "1"


def _is_lenient() -> bool:
    """Whether missing example files should render admonitions instead of failing."""
    return os.environ.get(LENIENT_ENV_VAR) == LENIENT_ENABLED


def on_page_markdown(markdown: str, page: Page, config: Config, files: Files) -> str:
    """Process markdown before conversion to HTML.

    This hook runs before markdown is converted to HTML, allowing us to:
    - Replace #! directives with full example files
    - Generate tabbed package manager commands

    Args:
        markdown: The raw markdown content
        page: The current page being processed
        config: MkDocs configuration
        files: All files in the documentation

    Returns:
        Processed markdown content
    """
    # Render full example files
    markdown = render_example_files(markdown, page)

    # Convert package manager commands to tabs
    markdown = create_package_manager_tabs(markdown)

    return markdown


def render_example_files(markdown: str, page: Page) -> str:
    """Replace #! directives with full example file contents.

    Syntax:
        #! src/hother/streamblocks_examples/00_quickstart/01_hello_world.py

    Paths are resolved relative to the repository root.

    Features:
    - Strips leading module docstrings
    - Adds syntax highlighting
    - Generates GitHub source link
    - Fails the build when the referenced file is missing (set
      STREAMBLOCKS_DOCS_LENIENT=1 to render an error admonition instead,
      e.g. while live-editing with `mkdocs serve`)

    Args:
        markdown: Markdown content to process
        page: The page being processed (used for error reporting)

    Returns:
        Markdown with #! directives replaced by code blocks
    """
    # Pattern: #! followed by file path (at start of line)
    pattern = r"^#!\s*(.+\.py)\s*$"

    def replace_directive(match: re.Match[str]) -> str:
        """Replace a single #! directive with rendered code."""
        file_path = match.group(1).strip()

        # Resolve file path
        resolved_path = utils.resolve_file_path(file_path)
        if resolved_path is None:
            message = f"Example file not found: `{file_path}` (referenced in {page.file.src_path})"
            if _is_lenient():
                return f'!!! error "Example file not found"\n    Could not find: `{file_path}`'
            raise PluginError(message)

        try:
            # Read file content
            code = resolved_path.read_text()
        except OSError as e:
            message = f"Failed to read example file `{file_path}` (referenced in {page.file.src_path}): {e}"
            if _is_lenient():
                return f'!!! error "Failed to read example file"\n    Error reading `{file_path}`: {e}'
            raise PluginError(message) from e

        # Strip leading docstring for cleaner display
        code = utils.strip_leading_docstring(code)

        # Format as code block with GitHub link
        return utils.format_code_block(code, file_path)

    # Replace all #! directives
    return re.sub(pattern, replace_directive, markdown, flags=re.MULTILINE)


def create_package_manager_tabs(markdown: str) -> str:
    """Convert package manager commands to tabbed alternatives.

    Converts:
        ```bash
        pip install streamblocks
        ```

    To:
        === "pip"
            ```bash
            pip install streamblocks
            ```

        === "uv"
            ```bash
            uv add streamblocks
            ```

    Args:
        markdown: Markdown content to process

    Returns:
        Markdown with tabbed package manager commands
    """
    # Pattern: bash code blocks containing pip install or uv add
    pattern = r"```bash\n((?:pip install|uv (?:add|pip install))[^\n]+)\n```"

    def create_tabs(match: re.Match[str]) -> str:
        """Create tabbed alternatives for a package manager command."""
        command = match.group(1).strip()

        # Extract package name
        if "pip install" in command:
            package = command.replace("pip install", "").strip()
        elif "uv add" in command:
            package = command.replace("uv add", "").strip()
        elif "uv pip install" in command:
            package = command.replace("uv pip install", "").strip()
        else:
            # Don't modify if we can't parse it
            return match.group(0)

        # Skip if it's a complex command (contains && or other operators)
        if any(op in command for op in ["&&", "||", ";", "|"]):
            return match.group(0)

        # Generate tabbed interface (uv first as default)
        return f"""=== "uv"
    ```bash
    uv add {package}
    ```

=== "pip"
    ```bash
    pip install {package}
    ```"""

    # Replace all package manager commands
    return re.sub(pattern, create_tabs, markdown, flags=re.MULTILINE)


# Export hook functions
__all__ = ["on_page_markdown"]
