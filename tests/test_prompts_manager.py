"""Tests for the Jinja2 TemplateManager."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from jinja2 import TemplateNotFound

from hother.streamblocks.prompts.manager import TemplateManager

if TYPE_CHECKING:
    from pathlib import Path


def test_render_default_registry_template() -> None:
    manager = TemplateManager()
    output = manager.render(
        {"syntax_name": "X", "syntax_format": "fmt", "blocks": []},
        mode="registry",
    )
    assert "# Structured Block Output Format" in output


def test_render_default_single_template() -> None:
    manager = TemplateManager()
    block = {
        "name": "demo",
        "description": "",
        "usage": None,
        "content_format": None,
        "metadata_schema": {},
        "examples": [],
    }
    output = manager.render(
        {"syntax_name": "X", "syntax_format": "fmt", "block": block},
        mode="single",
    )
    assert "# demo Block" in output


def test_register_and_render_custom_string_template() -> None:
    manager = TemplateManager()
    manager.register_template("v2", "name={{ block.name }}", mode="single")
    output = manager.render({"block": {"name": "demo"}}, version="v2", mode="single")
    assert output == "name=demo"


def test_register_custom_template_from_path(tmp_path: Path) -> None:
    template_file = tmp_path / "tpl.jinja2"
    template_file.write_text("count={{ blocks | length }}", encoding="utf-8")
    manager = TemplateManager()
    manager.register_template("file", template_file, mode="both")
    assert manager.render({"blocks": [1, 2]}, version="file", mode="registry") == "count=2"
    assert manager.render({"blocks": [1, 2]}, version="file", mode="single") == "count=2"


def test_unknown_package_version_raises() -> None:
    manager = TemplateManager()
    with pytest.raises(TemplateNotFound):
        manager.get_template(version="does-not-exist", mode="registry")
