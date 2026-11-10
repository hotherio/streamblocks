"""Artifact-generation tasks with deterministic checks (no judge model).

Each task asks for files. A check receives the resulting project (path -> text)
and returns whether it is correct. Checks that run generated code do so in a
subprocess with a timeout; the tasks are small and benign, but this is still
model-written code running with your privileges.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

Project = dict[str, str]

_CHECK_TIMEOUT_SECONDS = 20
_CHECK_SCRIPT = "_check.py"


@dataclass(frozen=True)
class Task:
    """One artifact-generation task.

    Attributes:
        name: Unique task name
        family: Task family (function, project, edit, verbatim, document)
        prompt: What the user asks for
        check: Returns True when the resulting project is correct
        initial_files: Files that exist before the model answers
        expected_paths: Paths the answer is expected to write or edit
    """

    name: str
    family: str
    prompt: str
    check: Callable[[Project], bool]
    initial_files: Project = field(default_factory=dict[str, str])
    expected_paths: tuple[str, ...] = ()


def runs_ok(script: str) -> Callable[[Project], bool]:
    """A check that writes the project to a temporary directory and runs ``script`` in it."""

    def check(project: Project) -> bool:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for path, text in project.items():
                target = (root / path).resolve()
                if not target.is_relative_to(root):
                    return False
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text)
            (root / _CHECK_SCRIPT).write_text(dedent(script))
            try:
                result = subprocess.run(
                    [sys.executable, "-B", _CHECK_SCRIPT],
                    cwd=root,
                    capture_output=True,
                    timeout=_CHECK_TIMEOUT_SECONDS,
                    check=False,
                    env={**os.environ, "PYTHONPATH": str(root)},
                )
            except subprocess.TimeoutExpired:
                return False
            return result.returncode == 0

    return check


def equals(path: str, reference: str) -> Callable[[Project], bool]:
    """A check that the file at ``path`` is ``reference``, ignoring trailing line breaks."""

    def check(project: Project) -> bool:
        return project.get(path, "").rstrip("\n") == reference.rstrip("\n")

    return check


def contains_all(path: str, *needles: str) -> Callable[[Project], bool]:
    """A check that the file at ``path`` contains every needle."""

    def check(project: Project) -> bool:
        text = project.get(path)
        return text is not None and all(needle in text for needle in needles)

    return check


def _verbatim(name: str, path: str, reference: str) -> Task:
    reference = dedent(reference)
    prompt = (
        f"Save the following text, exactly as it is and with nothing added or removed, as the file `{path}`.\n\n"
        f"----- BEGIN -----\n{reference}----- END -----"
    )
    return Task(name=name, family="verbatim", prompt=prompt, check=equals(path, reference), expected_paths=(path,))


TEXTSTATS = dedent('''\
    """Small text statistics helpers."""

    import re

    WORD = re.compile(r"[A-Za-z']+")


    def words(text: str) -> list[str]:
        """Return the words of ``text`` in order."""
        return WORD.findall(text)


    def word_count(text: str) -> int:
        """Return the number of words in ``text``."""
        return len(words(text))


    def most_common(text: str) -> str | None:
        """Return the most frequent word, or None for empty text."""
        counts: dict[str, int] = {}
        for word in words(text):
            counts[word] = counts.get(word, 0) + 1
        if not counts:
            return None
        return max(counts, key=lambda word: counts[word])


    def average_word_length(text: str) -> float:
        """Return the mean word length, or 0.0 for empty text."""
        found = words(text)
        if not found:
            return 0.0
        return sum(len(word) for word in found) / len(found)


    def longest_word(text: str) -> str | None:
        """Return the longest word, or None for empty text."""
        found = words(text)
        if not found:
            return None
        return max(found, key=len)
    ''')

TASKS: tuple[Task, ...] = (
    Task(
        name="slugify",
        family="function",
        prompt=(
            "Write `src/slug.py` with a function `slugify(text: str) -> str` that lowercases the text, replaces every "
            "run of characters that are not ASCII letters or digits with a single hyphen, and strips leading and "
            "trailing hyphens."
        ),
        check=runs_ok("""
            from src.slug import slugify
            assert slugify("Hello, World!") == "hello-world"
            assert slugify("  A  --  b__c ") == "a-b-c"
            assert slugify("") == ""
            assert slugify("Already-fine-123") == "already-fine-123"
        """),
        expected_paths=("src/slug.py",),
    ),
    Task(
        name="duration",
        family="function",
        prompt=(
            "Write `src/duration.py` with a function `parse_duration(text: str) -> int` that converts strings such as "
            '"1h30m", "45s", "2h" or "1h2m3s" into a number of seconds. Units are h, m and s, in that order, each '
            "optional. Raise ValueError for an empty string or anything that does not match."
        ),
        check=runs_ok("""
            from src.duration import parse_duration
            assert parse_duration("1h30m") == 5400
            assert parse_duration("45s") == 45
            assert parse_duration("2h") == 7200
            assert parse_duration("1h2m3s") == 3723
            for bad in ("", "abc", "30m1h", "5"):
                try:
                    parse_duration(bad)
                except ValueError:
                    continue
                raise AssertionError(bad)
        """),
        expected_paths=("src/duration.py",),
    ),
    Task(
        name="rle",
        family="function",
        prompt=(
            "Write `src/rle.py` with two functions. `encode(text: str) -> str` run-length encodes letters, so "
            '"aaabcc" becomes "3a1b2c". `decode(text: str) -> str` reverses it. Counts can have several digits. '
            "The empty string maps to the empty string."
        ),
        check=runs_ok("""
            from src.rle import decode, encode
            assert encode("aaabcc") == "3a1b2c"
            assert encode("") == ""
            assert decode("3a1b2c") == "aaabcc"
            assert decode("12x") == "x" * 12
            assert decode(encode("zzzzzzzzzzzzyx")) == "zzzzzzzzzzzzyx"
        """),
        expected_paths=("src/rle.py",),
    ),
    Task(
        name="shapes",
        family="project",
        prompt=(
            "Create a small Python package in three files. `shapes/circle.py` defines `area(radius: float) -> float` "
            "using math.pi. `shapes/square.py` defines `area(side: float) -> float`. `shapes/__init__.py` imports "
            "both modules and defines `total_area(circles: list[float], squares: list[float]) -> float`, the sum of "
            "all the areas."
        ),
        check=runs_ok("""
            import math
            import shapes
            from shapes import circle, square
            assert abs(circle.area(2) - math.pi * 4) < 1e-9
            assert square.area(3) == 9
            assert abs(shapes.total_area([1], [2, 3]) - (math.pi + 13)) < 1e-9
            assert shapes.total_area([], []) == 0
        """),
        expected_paths=("shapes/circle.py", "shapes/square.py", "shapes/__init__.py"),
    ),
    Task(
        name="inventory",
        family="project",
        prompt=(
            "Create two files. `inventory/models.py` defines a dataclass `Item` with fields `name: str`, "
            "`price: float` and `quantity: int`. `inventory/store.py` imports Item and defines a class `Store` with "
            "`add(item: Item) -> None`, `remove(name: str) -> None` (raise KeyError if the name is unknown) and "
            "`total_value() -> float`, the sum of price times quantity. Adding an item whose name already exists "
            "replaces it. Also create an empty `inventory/__init__.py`."
        ),
        check=runs_ok("""
            from inventory.models import Item
            from inventory.store import Store
            store = Store()
            store.add(Item("pen", 1.5, 4))
            store.add(Item("book", 10.0, 2))
            assert store.total_value() == 26.0
            store.add(Item("pen", 2.0, 1))
            assert store.total_value() == 22.0
            store.remove("book")
            assert store.total_value() == 2.0
            try:
                store.remove("book")
            except KeyError:
                pass
            else:
                raise AssertionError("KeyError expected")
        """),
        expected_paths=("inventory/models.py", "inventory/store.py", "inventory/__init__.py"),
    ),
    Task(
        name="edit_case",
        family="edit",
        prompt=(
            "In the existing file `src/textstats.py`, make `most_common` case-insensitive: it must count words "
            "regardless of case and return the winning word in lowercase. Change nothing else in the file."
        ),
        check=runs_ok("""
            from src.textstats import average_word_length, longest_word, most_common, word_count, words
            assert most_common("The the THE cat") == "the"
            assert most_common("") is None
            assert words("Hello there") == ["Hello", "there"]
            assert word_count("a b c") == 3
            assert average_word_length("ab abcd") == 3.0
            assert longest_word("a abc ab") == "abc"
        """),
        initial_files={"src/textstats.py": TEXTSTATS},
        expected_paths=("src/textstats.py",),
    ),
    Task(
        name="edit_add",
        family="edit",
        prompt=(
            "In the existing file `src/textstats.py`, add a function `shortest_word(text: str) -> str | None` at the "
            "end of the file. It returns the shortest word, or None for empty text. Change nothing else in the file."
        ),
        check=runs_ok("""
            from src.textstats import longest_word, most_common, shortest_word, word_count
            assert shortest_word("abc a ab") == "a"
            assert shortest_word("") is None
            assert longest_word("a abc ab") == "abc"
            assert most_common("x x y") == "x"
            assert word_count("a b") == 2
        """),
        initial_files={"src/textstats.py": TEXTSTATS},
        expected_paths=("src/textstats.py",),
    ),
    _verbatim(
        "verbatim_regex",
        "src/patterns.py",
        r"""
        import re

        ASSIGNMENT = re.compile(r"^\s*(\w+)\s*=\s*\"([^\"\\]*(?:\\.[^\"\\]*)*)\"\s*$")
        WINDOWS_PATH = re.compile(r"^[A-Za-z]:\\(?:[^\\/:*?\"<>|\r\n]+\\)*[^\\/:*?\"<>|\r\n]*$")
        TAG = re.compile(r"<(/?)(\w+)((?:\s+[\w-]+=(?:\"[^\"]*\"|'[^']*'))*)\s*(/?)>")
        ESCAPES = {"\\n": "\n", "\\t": "\t", "\\\\": "\\", "\\\"": "\""}
        """[1:],
    ),
    _verbatim(
        "verbatim_json",
        "src/fixtures.py",
        r'''
        PAYLOAD = "{\"user\": {\"name\": \"Ada \\\"the first\\\" Lovelace\", \"path\": \"C:\\\\Users\\\\ada\"}}"
        TEMPLATE = """{
          "greeting": "He said \"hi\"\n",
          "pattern": "^\\d{3}-\\d{4}$",
          "nested": {"quote": "'single' and \"double\""}
        }"""
        RAW = r'\d+\.\d*\s"quoted"\\'
        '''[1:],
    ),
    _verbatim(
        "verbatim_shell",
        "scripts/deploy.sh",
        r"""
        #!/usr/bin/env bash
        set -euo pipefail
        NAME="${1:-world}"
        printf 'Hello, %s!\n' "$NAME"
        echo "Today is $(date +"%Y-%m-%d") and \$HOME is \"$HOME\""
        sed -E 's/"([^"\\]|\\.)*"/"<redacted>"/g' <<'EOF'
        {"token": "a\"b\\c", "ok": true}
        EOF
        awk -F'\t' '{ print $1 "\\t" $2 }' data.tsv
        """[1:],
    ),
    Task(
        name="guide",
        family="document",
        prompt=(
            "Write `docs/guide.md`, a short usage guide for a package called shapes. It must have a top-level heading "
            "`# Usage`, a fenced `bash` code block containing the line `pip install shapes`, and a fenced `python` "
            "code block containing the line `from shapes import total_area`."
        ),
        check=contains_all(
            "docs/guide.md",
            "# Usage",
            "```bash\n",
            "pip install shapes\n",
            "```python\n",
            "from shapes import total_area",
        ),
        expected_paths=("docs/guide.md",),
    ),
)

TASKS_BY_NAME = {task.name: task for task in TASKS}
