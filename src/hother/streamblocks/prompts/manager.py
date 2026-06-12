"""Jinja2 template management for prompt generation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, PackageLoader, Template

if TYPE_CHECKING:
    from typing import Any

# Template render modes
_MODE_REGISTRY = "registry"
_MODE_SINGLE = "single"
_MODE_BOTH = "both"
_DEFAULT_VERSION = "default"


class TemplateManager:
    """Manage Jinja2 templates with version support for prompt A/B testing.

    Built-in templates live in the package ``templates/`` directory and are
    named ``<mode>.jinja2`` (default version) or ``<mode>_<version>.jinja2``.
    Custom templates can be registered at runtime via :meth:`register_template`.
    """

    def __init__(self) -> None:
        """Initialize the manager with the package template loader."""
        self._custom_templates: dict[tuple[str, str], Template] = {}
        self._env = Environment(
            loader=PackageLoader("hother.streamblocks.prompts", "templates"),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def register_template(self, version: str, template: str | Path, mode: str = _MODE_BOTH) -> None:
        """Register a custom template for one or both render modes.

        Args:
            version: Version identifier (e.g. "concise").
            template: Template string, or a Path to a template file.
            mode: "registry", "single", or "both".
        """
        template_str = template.read_text(encoding="utf-8") if isinstance(template, Path) else template
        template_obj = Template(template_str, autoescape=False, trim_blocks=True, lstrip_blocks=True)

        if mode in (_MODE_REGISTRY, _MODE_BOTH):
            self._custom_templates[(_MODE_REGISTRY, version)] = template_obj
        if mode in (_MODE_SINGLE, _MODE_BOTH):
            self._custom_templates[(_MODE_SINGLE, version)] = template_obj

    def get_template(self, version: str = _DEFAULT_VERSION, mode: str = _MODE_REGISTRY) -> Template:
        """Return the template for the given version and mode.

        Custom-registered templates take priority over built-in package
        templates.
        """
        custom = self._custom_templates.get((mode, version))
        if custom is not None:
            return custom

        filename = f"{mode}.jinja2" if version == _DEFAULT_VERSION else f"{mode}_{version}.jinja2"
        return self._env.get_template(filename)

    def render(self, context: dict[str, Any], version: str = _DEFAULT_VERSION, mode: str = _MODE_REGISTRY) -> str:
        """Render the resolved template with the given context."""
        return self.get_template(version, mode).render(context)
