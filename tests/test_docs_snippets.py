"""Guard against documentation/code drift in snippet references.

The docs build already fails on missing snippet targets (pymdownx
``check_paths`` and the ``#!`` hook raising ``PluginError``), but this test
surfaces the same drift in the regular pytest loop, without building docs.

Checked mechanisms:
- pymdownx scissor includes: ``--8<-- "path/to/file.py:section"``
- full-file example injection: ``#! path/to/file.py``
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DOCS_DIR = REPO_ROOT / "docs"

# --8<-- "src/.../file.py" or --8<-- "src/.../file.py:section"
SCISSOR_PATTERN = re.compile(r'--8<--\s+"(?P<path>[^":]+)(?::(?P<section>[\w-]+))?"')
# #! src/.../file.py (whole line, same pattern as docs/.hooks/main.py)
EXAMPLE_DIRECTIVE_PATTERN = re.compile(r"^#!\s*(?P<path>.+\.py)\s*$", re.MULTILINE)

SECTION_START_TEMPLATE = "--8<-- [start:{section}]"


def _doc_pages() -> list[Path]:
    """All markdown pages in the documentation tree."""
    return sorted(DOCS_DIR.rglob("*.md"))


def test_docs_dir_exists() -> None:
    """The documentation tree must be present."""
    assert DOCS_DIR.is_dir()


def test_scissor_snippet_targets_exist() -> None:
    """Every --8<-- include must point to an existing file and section."""
    failures: list[str] = []

    for page in _doc_pages():
        text = page.read_text()
        for match in SCISSOR_PATTERN.finditer(text):
            target = REPO_ROOT / match.group("path")
            relative_page = page.relative_to(REPO_ROOT)

            if not target.is_file():
                failures.append(f"{relative_page}: missing snippet file {match.group('path')}")
                continue

            section = match.group("section")
            if section is None:
                continue

            section_marker = SECTION_START_TEMPLATE.format(section=section)
            if section_marker not in target.read_text():
                failures.append(f"{relative_page}: section '{section}' not found in {match.group('path')}")

    assert not failures, "Docs snippet drift detected:\n" + "\n".join(failures)


def test_example_directive_targets_exist() -> None:
    """Every #! full-file injection must point to an existing file."""
    failures: list[str] = []

    for page in _doc_pages():
        text = page.read_text()
        for match in EXAMPLE_DIRECTIVE_PATTERN.finditer(text):
            target = REPO_ROOT / match.group("path")
            if not target.is_file():
                relative_page = page.relative_to(REPO_ROOT)
                failures.append(f"{relative_page}: missing example file {match.group('path')}")

    assert not failures, "Docs example-injection drift detected:\n" + "\n".join(failures)
