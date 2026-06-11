# AGENTS.md

Canonical engineering conventions for Streamblocks, for human contributors and AI
agents alike. These are **enforced contracts**, not suggestions: most are checked by
`basedpyright` strict, `ruff`, `lefthook`, and the 100%-coverage gate. If a rule blocks
you, change the rule deliberately (and this file) rather than working around it.

## Toolchain

- **Package/dev manager:** `uv`. Run everything through `uv run <cmd>`.
- **Python:** 3.13+ (basedpyright targets 3.14). Use modern syntax: PEP 695 generics
  (`class Foo[T]:`, `type Alias = ...`), `X | None` unions, `StrEnum`.
- **Type checker:** `basedpyright` in **strict** mode (`[tool.pyright]` in `pyproject.toml`).
- **Linter/formatter:** `ruff` — 120-col lines, double quotes, ~38 rule groups.
- **Hooks:** `lefthook`. **Build:** `hatchling`. **Docs:** MkDocs Material. **Releases:**
  `python-semantic-release` driven by conventional commits.

## Hard rules (contracts)

1. **No `# type: ignore`, no `# noqa`.** If the type system fights you, fix the types,
   restructure, or use a narrow `typing.cast(...)` with a one-line comment explaining
   *why* the cast is sound. `reportUnnecessaryTypeIgnoreComment` is an error, so a stale
   ignore fails CI anyway. (See `core/parsing.py`, `core/processor.py` for examples of
   `cast` used to express genuinely dynamic behavior.)
2. **No magic values in comparisons.** Name constants (e.g. `core/constants.py` `LIMITS`).
3. **`__all__` is mandatory and exhaustive** in public modules, grouped by category with
   comments (see `src/hother/streamblocks/__init__.py`).
4. **Google-style docstrings** on public classes/functions, including a `Raises:` section
   naming the exception type when one is raised.
5. **100% branch coverage.** `fail_under = 100`. Cover new branches with tests; reserve
   `# pragma: no cover` for genuinely unreachable internal guards, with a reason.
6. **Conventional commits**, atomic. **Never** `git commit --no-verify`. **Never**
   `git push` without being asked.

## Typing

- Annotate all public surfaces; `reportUnknownMemberType`/`reportUnknownParameterType`
  are errors.
- Prefer **Protocols** (`@runtime_checkable` where needed) over duck typing for
  structural contracts (see `adapters/protocols.py`).
- Put annotation-only imports under `if TYPE_CHECKING:` (with `from __future__ import
  annotations`), so they don't run at import time.
- `Any` is allowed only where genuinely unavoidable (heterogeneous registries, dynamic
  descriptors); keep it contained and documented.

## Errors: exceptions vs. events

Two distinct channels — do not collapse them:

- **`StreamblocksError` hierarchy** (`core/exceptions.py`) — raised **synchronously** for
  programmer/configuration errors (adapter not configured, no adapter detected for a chunk
  type, bad syntax argument). Flat subclasses with typed attributes and helpful messages.
  Consumers `except StreamblocksError`.
- **`BlockErrorEvent` / `BlockErrorCode`** (`core/types.py`) — emitted **as data into the
  stream** for per-block runtime problems (validation failed, size exceeded, unclosed
  block). These are not exceptions.

When raising inside an `except`, chain with `raise NewError(...) from exc`.

## Testing

- `pytest` with `asyncio_mode = "auto"`; tests live in `tests/` mirroring `src/`.
- The suite runs **shuffled** (`pytest-randomly`) and **in parallel** (`pytest-xdist -n
  auto`) with `xfail_strict = true` — keep tests order-independent; fix leaks rather than
  pinning a seed.
- Property-based tests via `hypothesis` where it adds value.

## Everyday commands

```bash
uv run lefthook run pre-commit --all-files -- --no-stash   # ruff + basedpyright + secrets
uv run pytest                                              # shuffled, parallel, 100% cov gate
uv run python src/hother/streamblocks_examples/run_examples.py   # all examples must pass
uv run mkdocs serve                                        # preview docs
```

Always run lefthook **with** `--no-stash` (keeps your working changes in place).

## Pull requests

Branch off `main`, conventional-commit PR title, link the issue, ensure pre-commit +
`pytest` + the example runner are green. See `docs/contributing.md` for the full workflow.
