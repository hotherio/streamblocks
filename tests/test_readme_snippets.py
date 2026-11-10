"""Guard the README code examples against drift from the public API."""

from __future__ import annotations

import ast
import importlib
import re
import subprocess
import sys
from pathlib import Path

import pytest

README = Path(__file__).parent.parent / "README.md"
PACKAGE_PREFIX = "hother.streamblocks"
PYTHON_BLOCK_PATTERN = re.compile(r"^```python\n(?P<code>.*?)^```$", re.MULTILINE | re.DOTALL)
RUNNABLE_MARKER = "asyncio.run(main())"
SNIPPET_TIMEOUT_SECONDS = 60


def _python_blocks() -> list[str]:
    return [match.group("code") for match in PYTHON_BLOCK_PATTERN.finditer(README.read_text())]


def test_readme_has_python_examples() -> None:
    assert _python_blocks()


@pytest.mark.parametrize("code", _python_blocks())
def test_readme_imports_exist(code: str) -> None:
    """Every name imported from the package in a README example must exist."""
    missing: list[str] = []
    for node in ast.walk(ast.parse(code)):
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        root = node.module.split(".")[0]
        if root == "streamblocks":
            missing.append(f"{node.module} (the import path is {PACKAGE_PREFIX})")
        if not node.module.startswith(PACKAGE_PREFIX):
            continue
        module = importlib.import_module(node.module)
        missing.extend(f"{node.module}.{alias.name}" for alias in node.names if not hasattr(module, alias.name))
    assert not missing, f"README imports names that do not exist: {missing}"


@pytest.mark.parametrize("code", [block for block in _python_blocks() if RUNNABLE_MARKER in block])
def test_readme_runnable_examples_extract_a_block(code: str) -> None:
    """Self-contained README examples must run and print something."""
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=SNIPPET_TIMEOUT_SECONDS, check=False
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip(), "example ran but extracted nothing"
