"""Streaming build: each file is checked as soon as it is written, and only failures are reported.

The model writes five small modules on top of a library whose documentation is out of date. The first
check that fails says what changed. What matters is how many files are written on the wrong assumption
before the model hears about it, and how long the whole build takes.

Checks run the code the model wrote, in a subprocess with a timeout.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from benchmarks.reactive.clock import COSTS, CostModel
from benchmarks.reactive.loop import Delivery, Record, Run
from hother.streamblocks import Registry, XmlTagSyntax
from hother.streamblocks.blocks.artifacts import ARTIFACT_BLOCKS, FILE_BLOCK_TYPE

if TYPE_CHECKING:
    from benchmarks.reactive.backend import Backend
    from hother.streamblocks.core.types import BlockEndEvent

_CHECK_TIMEOUT_S = 10
_ERROR_LENGTH = 300
SYSTEM_PROMPT = """You are a coding agent working in a build pipeline. You answer with files and nothing else: \
no explanation, no markdown fences, no text between files.

# Output format

Each file is one artifact block, exactly:

<artifact type="file" id="<short id>" path="<path>">
<the complete file>
</artifact>

The opening tag and the closing tag are each alone on their own line. The content is written verbatim, \
with no escaping. Example with two files:

<artifact type="file" id="greet" path="greet.py">
def greet(name):
    return "hello " + name
</artifact>
<artifact type="file" id="shout" path="shout.py">
def shout(text):
    return text.upper()
</artifact>

# Pipeline

Each file is checked automatically as soon as its block ends: the pipeline imports it and runs its tests. \
A check that passes is silent. A check that fails is reported with an event block:

<artifact type="event" id="e<N>">
Check failed for <path>: <error>
</artifact>

An event block can arrive at any moment, even in the middle of your own output, right after one of your \
files. Never write an event block yourself. When one appears:

- write the failed file again, complete, with the same path;
- apply what the error taught you to every file you write afterwards;
- if a file you already wrote has the same mistake and no event was reported for it yet, write it again too;
- do not write again files that are correct;
- then carry on with the files that are still missing.

Stop when every requested file is written and no check is failing.

# Conventions

- Python 3.13, standard library only, plus the libraries the task names.
- One module per file, at the project root. No packages, no `__main__` section, no tests, no prints.
- Functions are plain module-level functions with the exact names and arguments the task gives.
- Every function opens the store it needs itself, from the `path` argument. Keep no global state.
- Return plain built-in types (int, str, list, tuple, dict, None)."""

KVSTORE_DOCS = """# kvstore 1.4

A small key-value store. Keys are strings. Values are any JSON-serialisable value (str, int, float, bool,
None, list, dict). A value you get back is a copy: changing it does not change the store until you put it again.

    import kvstore

    store = kvstore.open(path)        # path: str. The store is created if it does not exist.
    store.put(key, value)             # set or replace the value of a key
    store.get(key, default=None)      # the value of a key, or `default` if the key is absent
    store.delete(key)                 # remove a key; does nothing if the key is absent
    store.keys()                      # every key, as a sorted list of str

Two stores opened with the same path share the same data. Stores opened with different paths are independent.
There is nothing to close or flush.

Example:

    store = kvstore.open("app.db")
    visits = store.get("visits", 0)
    store.put("visits", visits + 1)
"""

_KVSTORE_SOURCE = '''"""kvstore 2.0"""
import json

CHANGE = "{change}"
_FILES = {{}}
_RENAMED = {{"put": "write", "get": "read"}}


class Store:
    def __init__(self, path):
        self._data = _FILES.setdefault(str(path), {{}})

    def _put(self, key, value):
        if CHANGE == "strings" and not isinstance(value, str):
            kind = type(value).__name__
            raise TypeError("kvstore 2.0: values must be str, got " + kind + "; encode them with json.dumps")
        self._data[key] = json.dumps(value)

    def _get(self, key, default=None):
        return json.loads(self._data[key]) if key in self._data else default

    def delete(self, key):
        self._data.pop(key, None)

    def keys(self):
        return sorted(self._data)

    def __getattr__(self, name):
        names = {{"put": self._put, "get": self._get}}
        if CHANGE == "rename":
            if name in _RENAMED:
                raise AttributeError("kvstore 2.0: Store." + name + " was renamed to Store." + _RENAMED[name])
            names = {{"write": self._put, "read": self._get}}
        if name in names:
            return names[name]
        raise AttributeError("Store has no attribute " + name)


def connect(path):
    return Store(path)


def open(path):
    if CHANGE == "connect":
        raise RuntimeError("kvstore 2.0: kvstore.open(path) was removed, use kvstore.connect(path)")
    return Store(path)
'''


@dataclass(frozen=True)
class Module:
    path: str
    spec: str
    test: str


MODULES = (
    Module(
        "counter.py",
        "`increment(path, name)` adds one to the counter called `name` and returns its new value. "
        "A counter that does not exist yet starts at 0, so the first call returns 1.",
        """from counter import increment
assert increment("p", "a") == 1
assert increment("p", "a") == 2
assert increment("p", "b") == 1
assert increment("q", "a") == 1
""",
    ),
    Module(
        "settings.py",
        "`set_setting(path, key, value)` stores a setting. `get_setting(path, key, default=None)` returns it, "
        "or `default` if it was never set. Values can be str or int.",
        """from settings import get_setting, set_setting
assert get_setting("p", "theme") is None
assert get_setting("p", "theme", "light") == "light"
set_setting("p", "theme", "dark")
assert get_setting("p", "theme") == "dark"
set_setting("p", "size", 12)
assert get_setting("p", "size") == 12
""",
    ),
    Module(
        "tags.py",
        "`add_tag(path, item, tag)` adds a tag to an item; adding the same tag twice keeps one. "
        "`tags_of(path, item)` returns the item's tags as a sorted list, empty if it has none.",
        """from tags import add_tag, tags_of
assert tags_of("p", "x") == []
add_tag("p", "x", "b")
add_tag("p", "x", "a")
add_tag("p", "x", "b")
assert tags_of("p", "x") == ["a", "b"]
assert tags_of("p", "y") == []
""",
    ),
    Module(
        "sessions.py",
        "`login(path, user)` marks a user as logged in. `logout(path, user)` marks them as logged out and does "
        "nothing for an unknown user. `active(path)` returns the logged-in users as a sorted list.",
        """from sessions import active, login, logout
assert active("p") == []
login("p", "zoe")
login("p", "adam")
login("p", "zoe")
assert active("p") == ["adam", "zoe"]
logout("p", "zoe")
logout("p", "nobody")
assert active("p") == ["adam"]
""",
    ),
    Module(
        "scores.py",
        "`record(path, player, points)` adds points to a player's total. `leaderboard(path)` returns a list of "
        "`(player, total)` tuples, highest total first.",
        """from scores import leaderboard, record
record("p", "ann", 5)
record("p", "bob", 7)
record("p", "ann", 4)
assert [tuple(row) for row in leaderboard("p")] == [("ann", 9), ("bob", 7)]
""",
    ),
)
TESTS = {module.path: module.test for module in MODULES}


@dataclass(frozen=True)
class Scenario:
    """`name` is what changed in the installed library since the documentation was written."""

    name: str
    check_s: float = 1.0  # virtual seconds a check takes

    @property
    def task(self) -> str:
        specs = "\n".join(f"{n}. `{module.path}`: {module.spec}" for n, module in enumerate(MODULES, 1))
        return (
            "Write these five modules, in this order. Each stores its data with the installed `kvstore` library, "
            f"in the store at `path`.\n\n{specs}\n\nThe documentation we have for the library:\n\n{KVSTORE_DOCS}"
        )

    @property
    def library(self) -> str:
        return _KVSTORE_SOURCE.format(change=self.name)


SCENARIOS = [Scenario("rename"), Scenario("connect"), Scenario("strings")]


def check(scenario: Scenario, path: str, source: str) -> str | None:
    """Run the tests of one file. Returns the error, or None when they pass."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "kvstore.py").write_text(scenario.library)
        (root / path).write_text(source)
        (root / "_check.py").write_text(TESTS[path])
        try:
            result = subprocess.run(
                [sys.executable, "-B", "_check.py"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=_CHECK_TIMEOUT_S,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return "the check timed out"
    if result.returncode == 0:
        return None
    lines = result.stderr.strip().splitlines()
    return (lines[-1] if lines else "the check failed")[:_ERROR_LENGTH]


@dataclass
class Episode(Record):
    files_passing: int = 0
    checks: int = 0
    failed_checks: int = 0
    wasted_tokens: int = 0  # tokens of the files whose check failed
    events_delivered: int = 0
    call_log: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])


def run_episode(
    backend: Backend,
    scenario: Scenario,
    delivery: Delivery,
    *,
    max_tokens: int = 4000,
    cost: CostModel = COSTS["local"],
) -> Episode:
    return _Run(backend, scenario, delivery, cost).run(max_tokens)


class _Run(Run[Episode]):
    def __init__(self, backend: Backend, scenario: Scenario, delivery: Delivery, cost: CostModel) -> None:
        episode = Episode(task=scenario.name, delivery=delivery.value)
        registry = Registry(syntax=XmlTagSyntax(), blocks={FILE_BLOCK_TYPE: ARTIFACT_BLOCKS[FILE_BLOCK_TYPE]})
        super().__init__(backend, episode, delivery, SYSTEM_PROMPT, scenario.task, cost, registry)
        self.scenario = scenario
        self.failing: dict[str, bool] = {}  # path -> whether its latest version fails
        self.pending: list[tuple[float, str]] = []  # (virtual time the result is known, event text)
        self.ready = 0
        self.calls_before = len(getattr(backend, "call_log", []))

    def due(self, *, idle: bool) -> str | None:
        if not self.pending:
            return None
        if idle:  # the model has stopped: wait for the checks still running
            self.clock.now = max(self.clock.now, self.pending[-1][0])
        self.ready = sum(at <= self.clock.now for at, _ in self.pending)
        return "".join(text for _, text in self.pending[: self.ready]) or None

    def delivered(self) -> None:
        del self.pending[: self.ready]
        self.record.events_delivered += self.ready

    def block_closed(self, event: BlockEndEvent) -> None:
        path = str(event.metadata.get("path", ""))
        if event.block_type != FILE_BLOCK_TYPE or path not in TESTS:
            return
        episode = self.record
        error = check(self.scenario, path, str(event.content["raw_content"]) + "\n")
        episode.checks += 1
        self.failing[path] = error is not None
        if error is not None:
            episode.failed_checks += 1
            episode.wasted_tokens += episode.completion_tokens - self.block_started_at
            number = episode.failed_checks
            text = f'<artifact type="event" id="e{number}">\nCheck failed for {path}: {error}\n</artifact>\n'
            self.pending.append((self.clock.now + self.scenario.check_s, text))

    def score(self) -> None:
        """Compliant: the latest version of every requested file passes its check."""
        episode = self.record
        episode.files_passing = sum(self.failing.get(path) is False for path in TESTS)
        episode.compliant = episode.files_passing == len(TESTS)
        episode.call_log = list(getattr(self.backend, "call_log", [])[self.calls_before :])
