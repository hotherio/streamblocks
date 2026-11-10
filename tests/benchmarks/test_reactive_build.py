"""Build scenario logic, driven by a scripted backend (no model). Checks run real subprocesses."""

from benchmarks.reactive.backend import ScriptedBackend
from benchmarks.reactive.build import MODULES, Scenario, check, run_episode
from benchmarks.reactive.clock import CostModel
from benchmarks.reactive.loop import Delivery

ONE_PIECE_PER_SECOND = CostModel(decode_tps=1, prefill_tps=float("inf"), call_overhead_s=0)
RENAME = Scenario("rename", check_s=1.0)
BODIES = {
    "counter.py": "def increment(path, name):\n    s = kvstore.open(path)\n    n = s.GET(name, 0) + 1\n    s.PUT(name, n)\n    return n",
    "settings.py": "def set_setting(path, key, value):\n    kvstore.open(path).PUT(key, value)\n\ndef get_setting(path, key, default=None):\n    return kvstore.open(path).GET(key, default)",
    "tags.py": "def add_tag(path, item, tag):\n    s = kvstore.open(path)\n    s.PUT(item, sorted({*s.GET(item, []), tag}))\n\ndef tags_of(path, item):\n    return kvstore.open(path).GET(item, [])",
    "sessions.py": "def login(path, user):\n    kvstore.open(path).PUT(user, True)\n\ndef logout(path, user):\n    kvstore.open(path).delete(user)\n\ndef active(path):\n    return kvstore.open(path).keys()",
    "scores.py": "def record(path, player, points):\n    s = kvstore.open(path)\n    s.PUT(player, s.GET(player, 0) + points)\n\ndef leaderboard(path):\n    s = kvstore.open(path)\n    return sorted(((p, s.GET(p)) for p in s.keys()), key=lambda row: -row[1])",
}
PATHS = [module.path for module in MODULES]


def _source(path: str, *, new_api: bool) -> str:
    put, get = ("write", "read") if new_api else ("put", "get")
    return "import kvstore\n\n" + BODIES[path].replace("PUT", put).replace("GET", get) + "\n"


def _files(paths: list[str], *, new_api: bool) -> list[str]:
    """Three pieces per file: opening tag, content, closing tag."""
    return [
        piece
        for path in paths
        for piece in (f'<artifact type="file" id="f" path="{path}">\n', _source(path, new_api=new_api), "</artifact>\n")
    ]


def test_reference_modules_pass_with_the_new_api_and_fail_with_the_documented_one() -> None:
    for path in PATHS:
        assert check(RENAME, path, _source(path, new_api=True)) is None
        assert "was renamed to" in (check(RENAME, path, _source(path, new_api=False)) or "")


def test_inject_reports_the_first_failure_while_the_second_file_is_written() -> None:
    backend = ScriptedBackend([_files(PATHS, new_api=False)], after_inject=_files(PATHS, new_api=True))
    episode = run_episode(backend, RENAME, Delivery.INJECT, cost=ONE_PIECE_PER_SECOND)

    assert episode.compliant
    assert (episode.failed_checks, episode.llm_calls) == (2, 1)
    assert "Check failed for counter.py: AttributeError: kvstore 2.0: Store.get was renamed" in backend.injected[0]


def test_turn_boundary_writes_every_file_on_the_wrong_assumption() -> None:
    backend = ScriptedBackend([_files(PATHS, new_api=False), _files(PATHS, new_api=True)])
    episode = run_episode(backend, RENAME, Delivery.TURN_BOUNDARY, cost=ONE_PIECE_PER_SECOND)

    assert episode.compliant
    assert (episode.failed_checks, episode.events_delivered, episode.llm_calls) == (5, 5, 2)


def test_a_failure_left_unrepaired_is_not_compliant() -> None:
    backend = ScriptedBackend([_files(PATHS, new_api=False)], after_inject=_files(PATHS[2:], new_api=True))
    episode = run_episode(backend, RENAME, Delivery.INJECT, cost=ONE_PIECE_PER_SECOND)

    assert not episode.compliant
    assert episode.files_passing == len(PATHS[2:])
