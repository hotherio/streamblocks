"""Tests for the artifact benchmark harness, run against a scripted backend (no model)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from benchmarks.artifacts.arms import build_arms
from benchmarks.artifacts.backends import ScriptedBackend
from benchmarks.artifacts.episode import run_episode
from benchmarks.artifacts.run import load_records, run_matrix
from benchmarks.artifacts.summary import rate_interval, summarize
from benchmarks.artifacts.tasks import TASKS, TASKS_BY_NAME, TEXTSTATS

if TYPE_CHECKING:
    from pathlib import Path

SLUG = 'import re\n\n\ndef slugify(text: str) -> str:\n    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")'
GOOD_ANSWERS = {
    "xml": f'Here it is.\n<artifact type="file" id="a" path="src/slug.py">\n{SLUG}\n</artifact>\n',
    "frontmatter": f'!!start\n---\nid: "a"\nblock_type: file\npath: "src/slug.py"\n---\n{SLUG}\n!!end\n',
    "fenced": f"Here it is.\n\n```src/slug.py\n{SLUG}\n```\n",
    "json": json.dumps({"files": [{"path": "src/slug.py", "content": SLUG}]}),
}
ARMS = build_arms()


def _episode(arm: str, answer: str, task: str = "slugify", max_tokens: int = 10_000):
    backend = ScriptedBackend({"": answer})
    return run_episode(backend, ARMS[arm], TASKS_BY_NAME[task], seed=0, max_tokens=max_tokens, temperature=0.0)


@pytest.mark.parametrize(
    ("arm", "answer"),
    [(name, GOOD_ANSWERS[name.split("+")[0].removesuffix("-noex")]) for name in ARMS],
)
def test_correct_answer_passes_in_every_arm(arm: str, answer: str) -> None:
    episode = _episode(arm, answer)
    assert episode.score == 1.0
    assert episode.well_formed
    assert episode.artifacts == 1
    assert episode.malformed_by_code == {}
    assert episode.grammar is ("+" in arm)


def test_block_arm_sees_the_artifact_before_the_answer_ends() -> None:
    blocks = _episode("xml", GOOD_ANSWERS["xml"])
    fenced = _episode("fenced", GOOD_ANSWERS["fenced"])
    assert blocks.first_artifact_piece is not None
    assert blocks.first_artifact_piece < blocks.completion_tokens
    assert fenced.first_artifact_piece == fenced.completion_tokens


@pytest.mark.parametrize(
    ("arm", "answer", "code"),
    [
        ("xml", '<artifact type="file" id="a" path="src/slug.py">\nx = 1\n', "UNCLOSED_BLOCK"),
        ("xml", '<artifact type="file" id="a">\nx = 1\n</artifact>\n', "PARSE_FAILED"),
        ("xml", "I cannot help with that.\n", "NO_ARTIFACT"),
        ("json", '{"files": [{"path": "src/slug.py", "content": "x = "1""}]}', "INVALID_JSON"),
        ("fenced", "```python\nx = 1\n", "NO_ARTIFACT"),
    ],
)
def test_malformed_answers_are_counted(arm: str, answer: str, code: str) -> None:
    episode = _episode(arm, answer)
    assert episode.malformed_by_code == {code: 1}
    assert not episode.well_formed
    assert episode.score == 0.0


def test_patch_is_applied_to_the_initial_file() -> None:
    answer = (
        '<artifact type="patch" id="p" path="src/textstats.py">\n'
        "<<<<<<< SEARCH\n        counts[word] = counts.get(word, 0) + 1\n=======\n"
        "        counts[word.lower()] = counts.get(word.lower(), 0) + 1\n>>>>>>> REPLACE\n</artifact>\n"
    )
    episode = _episode("xml", answer, task="edit_case")
    assert episode.score == 1.0
    assert episode.well_formed

    missing = answer.replace("counts.get(word, 0)", "counts.get(w, 0)")
    failed = _episode("xml", missing, task="edit_case")
    assert failed.malformed_by_code == {"APPLY_FAILED": 1}
    assert failed.score == 0.0


def test_verbatim_tasks_are_byte_exact() -> None:
    task = TASKS_BY_NAME["verbatim_regex"]
    reference = task.prompt.split("----- BEGIN -----\n")[1].split("----- END -----")[0]
    exact = f'<artifact type="file" id="a" path="src/patterns.py">\n{reference}</artifact>\n'
    assert _episode("xml", exact, task="verbatim_regex").score == 1.0
    assert _episode("xml", exact.replace("\\\\", "\\", 1), task="verbatim_regex").score == 0.0
    as_json = json.dumps({"files": [{"path": "src/patterns.py", "content": reference}]})
    assert _episode("json", as_json, task="verbatim_regex").score == 1.0


def test_unchanged_initial_files_do_not_pass_edit_tasks() -> None:
    assert not TASKS_BY_NAME["edit_case"].check({"src/textstats.py": TEXTSTATS})
    assert not TASKS_BY_NAME["edit_add"].check({"src/textstats.py": TEXTSTATS})


def test_every_task_fails_on_an_empty_project() -> None:
    for task in TASKS:
        assert not task.check(dict(task.initial_files)), task.name


def test_truncation_is_recorded() -> None:
    episode = _episode("xml", GOOD_ANSWERS["xml"], max_tokens=5)
    assert episode.truncated
    assert episode.completion_tokens == 5
    assert episode.score == 0.0


def test_matrix_resumes_and_summarises(tmp_path: Path) -> None:
    out = tmp_path / "run.jsonl"
    backend = ScriptedBackend({"slugify": GOOD_ANSWERS["xml"]})
    options = {
        "arms": ["xml", "fenced"],
        "tasks": ["slugify", "rle"],
        "out": out,
        "max_tokens": 500,
        "temperature": 0.0,
    }
    run_matrix(backend, seeds=1, **options)
    assert len(load_records(out)) == 4
    out.write_text(out.read_text() + '{"torn": ')
    run_matrix(backend, seeds=2, **options)
    records = load_records(out)
    assert len(records) == 8

    rows = {row["arm"]: row for row in summarize(records)}
    assert rows["xml"]["n"] == 4
    assert rows["xml"]["pass"][0] == 0.5
    assert rows["fenced"]["pass"][0] == 0.0
    assert rows["xml"]["codes"] == {"NO_ARTIFACT": 2}


def test_rate_interval_bounds() -> None:
    mean, low, high = rate_interval([1.0, 0.0, 1.0, 1.0])
    assert mean == 0.75
    assert 0.0 <= low <= mean <= high <= 1.0
    assert rate_interval([]) == (0.0, 0.0, 0.0)


def test_unencodable_characters_do_not_stop_a_sweep() -> None:
    answer = GOOD_ANSWERS["xml"].replace("Here it is.", "Here it is \udddd.")
    episode = _episode("xml", answer)
    assert episode.error is None
    assert episode.score == 1.0
    assert "\udddd" not in episode.answer
    json.dumps(episode.to_record()).encode()
