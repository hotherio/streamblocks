"""Tests for the artifact stream demo, in replay mode (no model, no server)."""

from __future__ import annotations

from typing import Any

from demos.artifact_stream import server
from demos.artifact_stream.server import PRESETS, ReplayBackend, run


def _run(preset: str, *, guard: bool, monkeypatch: Any) -> list[dict[str, Any]]:
    monkeypatch.setattr(server, "REPLAY_DELAY_SECONDS", 0)
    return list(run(ReplayBackend(), PRESETS[preset], grammar=False, guard=guard))


def test_package_preset_writes_and_patches_files(monkeypatch: Any) -> None:
    messages = _run("package", guard=True, monkeypatch=monkeypatch)
    ends = [m for m in messages if m["type"] == "end"]
    assert [(m["path"], m["applied"]) for m in ends] == [
        ("src/shapes/circle.py", "written"),
        ("src/shapes/square.py", "written"),
        ("src/shapes/__init__.py", "written"),
        ("tests/test_shapes.py", "written"),
        ("src/shapes/square.py", "patched"),
    ]
    assert "with the given side length" in ends[-1]["content"]
    first_text = next(m["text"] for m in messages if m["type"] == "text" and m["text"])
    assert first_text.startswith("Here is the package")
    done = messages[-1]
    assert (done["type"], done["aborted"], done["artifacts"], done["malformed"]) == ("done", False, 5, 0)


def test_guard_stops_the_generation_at_the_rejected_file(monkeypatch: Any) -> None:
    guarded = _run("outside", guard=True, monkeypatch=monkeypatch)
    unguarded = _run("outside", guard=False, monkeypatch=monkeypatch)

    assert [m["path"] for m in guarded if m["type"] == "end"] == ["src/app.py"]
    (error,) = [m for m in guarded if m["type"] == "error"]
    assert error["code"] == "ABORTED"
    assert not [m for m in guarded if m["type"] == "delta" and "DEBUG" in m["line"]]
    assert guarded[-1]["aborted"]
    assert guarded[-1]["pieces"] < unguarded[-1]["pieces"]

    assert [m["path"] for m in unguarded if m["type"] == "end"] == ["src/app.py", "../.env"]
    assert not unguarded[-1]["aborted"]


def test_deltas_arrive_between_start_and_end(monkeypatch: Any) -> None:
    messages = _run("package", guard=False, monkeypatch=monkeypatch)
    first_block = messages[next(i for i, m in enumerate(messages) if m["type"] == "start")]["id"]
    kinds = [m["type"] for m in messages if m.get("id") == first_block]
    assert kinds[0] == "start"
    assert kinds[-1] == "end"
    assert set(kinds[1:-1]) == {"delta"}
