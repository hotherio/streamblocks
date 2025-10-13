"""Template management for prompt generation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, PackageLoader, Template

if TYPE_CHECKING:
    from typing import Any


class TemplateManager:
    """Manage Jinja2 templates with version support for A/B testing."""

    def __init__(self) -> None:
        """Initialize template manager."""
        self._custom_templates: dict[tuple[str, str], Template] = {}
        self._env = self._setup_jinja_env()

    def _setup_jinja_env(self) -> Environment:
        """Setup Jinja2 environment with package loader."""
        loader = PackageLoader("hother.streamblocks.prompts", "templates")
        return Environment(
            loader=loader,
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def register_template(self, version: str, template: str | Path, mode: str = "both") -> None:
        """Register custom template for specific mode(s).

        Args:
            version: Template version identifier (e.g., "v2", "concise")
            template: Template string or path to template file
            mode: Which mode to register for: "registry", "single", or "both"

        Example:
            >>> manager = TemplateManager()
            >>> manager.register_template("concise", "Block: {{ block.name }}", mode="single")
        """
        if isinstance(template, Path):
            template_str = template.read_text()
        else:
            template_str = template

        template_obj = Template(template_str, autoescape=False, trim_blocks=True, lstrip_blocks=True)

        # Register for specified modes
        if mode in ["registry", "both"]:
            self._custom_templates[("registry", version)] = template_obj
        if mode in ["single", "both"]:
            self._custom_templates[("single", version)] = template_obj

    def get_template(self, version: str = "default", mode: str = "registry") -> Template:
        """Get template by version and mode.

        Args:
            version: Template version (default: "default")
            mode: "registry" or "single"

        Returns:
            Jinja2 Template object

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        key = (mode, version)
        if key in self._custom_templates:
            return self._custom_templates[key]

        # Load from package
        filename = f"{mode}_{version}.jinja2" if version != "default" else f"{mode}.jinja2"
        return self._env.get_template(filename)

    def render(self, context: dict[str, Any], version: str = "default", mode: str = "registry") -> str:
        """Render template with context.

        Args:
            context: Template context dictionary
            version: Template version (default: "default")
            mode: "registry" or "single"

        Returns:
            Rendered template string

        Example:
            >>> manager = TemplateManager()
            >>> context = {
            ...     "syntax_name": "DelimiterPreambleSyntax",
            ...     "blocks": [...]
            ... }
            >>> prompt = manager.render(context, mode="registry")
        """
        template = self.get_template(version, mode)
        return template.render(context)
