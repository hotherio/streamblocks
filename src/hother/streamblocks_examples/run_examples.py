#!/usr/bin/env python3
"""Runner script for StreamBlocks examples.

This script discovers and runs all example scripts in the streamblocks_examples package,
with smart handling of TUI examples and API-dependent examples.

Usage:
    uv run python -m hother.streamblocks_examples.run_examples                    # Run all runnable examples
    uv run python -m hother.streamblocks_examples.run_examples --category 03_adapters # Run only adapter examples
    uv run python -m hother.streamblocks_examples.run_examples --skip-api         # Skip API-dependent examples
    uv run python -m hother.streamblocks_examples.run_examples --include-ui       # Include TUI examples (will likely fail)
    uv run python -m hother.streamblocks_examples.run_examples --dry-run          # Show what would be executed
    uv run python -m hother.streamblocks_examples.run_examples --parallel         # Run examples in parallel
    uv run python -m hother.streamblocks_examples.run_examples --timeout 60       # Set custom timeout (seconds)
"""

import asyncio
import os
import subprocess
import sys
from collections import defaultdict
from enum import StrEnum, auto
from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel, Field


class OutputFormat(StrEnum):
    """Output format options."""

    TEXT = auto()
    JSON = auto()


class ExampleInfo(BaseModel):
    """Information about an example script."""

    path: Path
    category: str
    requires_api_keys: list[str] = Field(default_factory=list)
    is_tui: bool = False
    timeout: int = 30

    model_config = {"frozen": True}


class ExampleResult(BaseModel):
    """Result of running a single example."""

    path: str
    status: str  # "pass" or "fail"
    category: str
    duration: float
    error: str | None = None


class ExampleSummary(BaseModel):
    """Summary of all example runs."""

    total: int
    passed: int
    failed: int
    skipped: int


class SkippedExample(BaseModel):
    """Information about a skipped example."""

    path: str
    reason: str
    category: str


class RunOutput(BaseModel):
    """Complete output structure for JSON mode."""

    summary: ExampleSummary
    results: list[ExampleResult]
    skipped: list[SkippedExample]


class ExampleRunner:
    """Discovers and runs example scripts."""

    def __init__(self, examples_dir: Path) -> None:
        self.examples_dir = examples_dir
        self.examples: list[ExampleInfo] = []

    def discover(self) -> list[ExampleInfo]:
        """Discover all example scripts."""
        examples = []

        for path in self.examples_dir.rglob("*.py"):
            # Skip __init__.py, this script, and helper modules
            if path.stem.startswith("_") or path.name == "run_examples.py":
                continue
            # Skip helper and tools directories
            rel_path = path.relative_to(self.examples_dir)
            if rel_path.parts[0] in ("helpers", "tools", "blocks"):
                continue

            # Determine category from folder structure
            category = rel_path.parts[0] if len(rel_path.parts) > 1 else "root"

            # Detect TUI examples
            is_tui = self._is_tui_example(path)

            # Detect API requirements
            api_keys = self._detect_api_requirements(path)

            examples.append(
                ExampleInfo(
                    path=path,
                    category=category,
                    requires_api_keys=api_keys,
                    is_tui=is_tui,
                )
            )

        self.examples = sorted(examples, key=lambda e: str(e.path))
        return self.examples

    def _is_tui_example(self, path: Path) -> bool:
        """Check if example is a TUI (Textual) application."""
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            return "from textual" in content or "import textual" in content
        except Exception:
            return False

    def _detect_api_requirements(self, path: Path) -> list[str]:
        """Detect which API keys an example requires."""
        api_keys = []
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")

            if "GEMINI_API_KEY" in content or "GOOGLE_API_KEY" in content:
                api_keys.append("GEMINI_API_KEY")
            if "OPENAI_API_KEY" in content:
                api_keys.append("OPENAI_API_KEY")
            if "ANTHROPIC_API_KEY" in content:
                api_keys.append("ANTHROPIC_API_KEY")

        except Exception:
            pass

        return api_keys

    def should_run(
        self,
        example: ExampleInfo,
        *,
        include_ui: bool = False,
        skip_api: bool = False,
        category_filter: str | None = None,
    ) -> tuple[bool, str]:
        """Determine if an example should be run.

        Returns:
            Tuple of (should_run, skip_reason)
        """
        # Check category filter
        if category_filter and example.category != category_filter:
            return False, f"category filter (want {category_filter}, got {example.category})"

        # Check TUI
        if example.is_tui and not include_ui:
            return False, "TUI example (requires user interaction)"

        # Check API keys
        if example.requires_api_keys and not skip_api:
            missing_keys = [key for key in example.requires_api_keys if not os.getenv(key)]
            if missing_keys:
                return False, f"missing API keys: {', '.join(missing_keys)}"

        if skip_api and example.requires_api_keys:
            return False, "skipping API examples (--skip-api)"

        return True, ""

    async def run_example(
        self,
        example: ExampleInfo,
        timeout: int = 30,
    ) -> tuple[bool, str, str]:
        """Run a single example.

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            # Add src directory to PYTHONPATH for hother.streamblocks_examples imports
            # examples_dir is src/hother/streamblocks_examples, so we need src/
            src_dir = str(self.examples_dir.parent.parent)
            env = os.environ.copy()
            existing_pythonpath = env.get("PYTHONPATH", "")
            paths = [src_dir]
            if existing_pythonpath:
                paths.append(existing_pythonpath)
            env["PYTHONPATH"] = ":".join(paths)

            result = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    sys.executable,
                    str(example.path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    stdin=asyncio.subprocess.DEVNULL,
                    env=env,
                ),
                timeout=timeout,
            )

            stdout_data, stderr_data = await result.communicate()
            stdout = stdout_data.decode("utf-8", errors="replace")
            stderr = stderr_data.decode("utf-8", errors="replace")

            success = result.returncode == 0 and "Traceback" not in stderr

            return success, stdout, stderr

        except TimeoutError:
            return False, "", f"Timeout after {timeout}s"
        except Exception as e:
            return False, "", f"Exception: {e}"

    def run_example_sync(
        self,
        example: ExampleInfo,
        timeout: int = 30,
    ) -> tuple[bool, str, str]:
        """Run a single example synchronously.

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            # Add src directory to PYTHONPATH for hother.streamblocks_examples imports
            # examples_dir is src/hother/streamblocks_examples, so we need src/
            src_dir = str(self.examples_dir.parent.parent)
            env = os.environ.copy()
            existing_pythonpath = env.get("PYTHONPATH", "")
            paths = [src_dir]
            if existing_pythonpath:
                paths.append(existing_pythonpath)
            env["PYTHONPATH"] = ":".join(paths)

            result = subprocess.run(
                [sys.executable, str(example.path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
                env=env,
            )

            success = result.returncode == 0 and "Traceback" not in result.stderr

            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return False, "", f"Timeout after {timeout}s"
        except Exception as e:
            return False, "", f"Exception: {e}"


def get_display_path(example: ExampleInfo, examples_dir: Path) -> str:
    """Get display path relative to examples directory."""
    try:
        rel_path = example.path.relative_to(examples_dir)
        return str(rel_path)
    except ValueError:
        # Fallback to absolute path
        return str(example.path)


def print_colored(text: str, color: str = "") -> None:
    """Print colored text."""
    colors = {
        "green": "\033[92m",
        "red": "\033[91m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "cyan": "\033[96m",
        "reset": "\033[0m",
        "bold": "\033[1m",
        "dim": "\033[2m",
    }
    if color and color in colors:
        print(f"{colors[color]}{text}{colors['reset']}")
    else:
        print(text)


async def main_async(
    category: str | None = None,
    skip_api: bool = False,
    include_ui: bool = False,
    dry_run: bool = False,
    parallel: bool = False,
    timeout: int = 30,
    verbose: bool = False,
    output: OutputFormat = OutputFormat.TEXT,
) -> int:
    """Main async entry point."""

    # Discover examples
    examples_dir = Path(__file__).parent
    runner = ExampleRunner(examples_dir)

    if output == OutputFormat.TEXT:
        print_colored("🔍 Discovering examples...", "cyan")
    examples = runner.discover()
    if output == OutputFormat.TEXT:
        print_colored(f"Found {len(examples)} example files\n", "cyan")

    # Filter examples
    to_run = []
    skipped: dict[str, list[ExampleInfo]] = defaultdict(list)

    for example in examples:
        should_run, skip_reason = runner.should_run(
            example,
            include_ui=include_ui,
            skip_api=skip_api,
            category_filter=category,
        )

        if should_run:
            to_run.append(example)
        else:
            skipped[skip_reason].append(example)

    # Print summary (text mode only)
    if output == OutputFormat.TEXT:
        print_colored(f"📋 Examples to run: {len(to_run)}", "bold")
        if skipped:
            print_colored(f"⏭️  Skipping {sum(len(v) for v in skipped.values())} examples:", "dim")
            for reason, examples_list in sorted(skipped.items()):
                print_colored(f"   - {len(examples_list)} ({reason})", "dim")
        print()

    if not to_run:
        if output == OutputFormat.TEXT:
            print_colored("❌ No examples to run!", "red")
        return 1

    # JSON output mode
    if output == OutputFormat.JSON:
        import time

        # Collect skipped examples using Pydantic models
        skipped_data = [
            SkippedExample(
                path=get_display_path(example, examples_dir),
                reason=reason,
                category=example.category,
            )
            for reason, examples_list in skipped.items()
            for example in examples_list
        ]

        # Run examples silently
        results_data = []
        for example in to_run:
            start_time = time.time()
            success, stdout, stderr = await runner.run_example(example, timeout=timeout)
            duration = time.time() - start_time

            result = ExampleResult(
                path=get_display_path(example, examples_dir),
                status="pass" if success else "fail",
                category=example.category,
                duration=round(duration, 2),
                error=stderr.strip().split("\n")[0] if not success and stderr else None,
            )

            results_data.append(result)

        # Build final output using Pydantic
        passed = sum(1 for r in results_data if r.status == "pass")
        failed = len(results_data) - passed

        run_output = RunOutput(
            summary=ExampleSummary(
                total=len(results_data),
                passed=passed,
                failed=failed,
                skipped=len(skipped_data),
            ),
            results=results_data,
            skipped=skipped_data,
        )

        print(run_output.model_dump_json(indent=2))
        return 0 if failed == 0 else 1

    # Text output mode
    # Dry run mode
    if dry_run:
        print_colored("🔎 Dry run - would execute:", "yellow")
        for example in to_run:
            display_path = get_display_path(example, examples_dir)
            api_info = f" [API: {', '.join(example.requires_api_keys)}]" if example.requires_api_keys else ""
            print(f"  • {display_path}{api_info}")
        return 0

    # Run examples
    print_colored("🚀 Running examples...\n", "bold")

    results: list[tuple[ExampleInfo, bool, str, str]] = []

    if parallel:
        # Run in parallel
        tasks = [runner.run_example(example, timeout=timeout) for example in to_run]
        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        for example, result in zip(to_run, task_results, strict=False):
            if isinstance(result, Exception):
                results.append((example, False, "", str(result)))
            else:
                success, stdout, stderr = result
                results.append((example, success, stdout, stderr))
    else:
        # Run sequentially
        for i, example in enumerate(to_run, 1):
            display_path = get_display_path(example, examples_dir)
            print(f"[{i}/{len(to_run)}] Running {display_path}...", end=" ", flush=True)

            success, stdout, stderr = await runner.run_example(example, timeout=timeout)
            results.append((example, success, stdout, stderr))

            if success:
                print_colored("✅ PASS", "green")
            else:
                print_colored("❌ FAIL", "red")

            if verbose or not success:
                if stdout.strip():
                    print_colored("  stdout:", "dim")
                    for line in stdout.strip().split("\n")[:10]:  # First 10 lines
                        print_colored(f"    {line}", "dim")
                if stderr.strip():
                    print_colored("  stderr:", "dim")
                    for line in stderr.strip().split("\n")[:10]:  # First 10 lines
                        print_colored(f"    {line}", "dim")

    # Print summary
    print()
    print_colored("=" * 70, "bold")
    print_colored("📊 Summary", "bold")
    print_colored("=" * 70, "bold")

    passed = sum(1 for _, success, _, _ in results if success)
    failed = len(results) - passed

    print(f"Total:  {len(results)}")
    print_colored(f"Passed: {passed}", "green")
    if failed > 0:
        print_colored(f"Failed: {failed}", "red")

    # Show failed examples
    if failed > 0:
        print()
        print_colored("❌ Failed examples:", "red")
        for example, success, _, stderr in results:
            if not success:
                display_path = get_display_path(example, examples_dir)
                print(f"  • {display_path}")
                if stderr:
                    # Show first line of error
                    first_error = stderr.strip().split("\n")[0]
                    print_colored(f"    {first_error}", "dim")

    # Show skipped summary by category
    if skipped:
        print()
        print_colored("⏭️  Skipped examples:", "yellow")
        for reason, examples_list in sorted(skipped.items()):
            print(f"  • {len(examples_list)} - {reason}")

    return 0 if failed == 0 else 1


# Create Typer app
app = typer.Typer(
    name="run_examples",
    help="Run StreamBlocks examples with smart filtering and output options",
    add_completion=False,
)


@app.command()
def main(
    category: Annotated[
        str | None,
        typer.Option(
            "--category",
            help="Run only examples from specific category (adapters, ui, logging, etc.)",
        ),
    ] = None,
    skip_api: Annotated[
        bool,
        typer.Option(
            "--skip-api",
            help="Skip examples that require API keys",
        ),
    ] = False,
    include_ui: Annotated[
        bool,
        typer.Option(
            "--include-ui",
            help="Include TUI examples (they will likely fail without interaction)",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show what would be executed without running",
        ),
    ] = False,
    parallel: Annotated[
        bool,
        typer.Option(
            "--parallel",
            help="Run examples in parallel (faster but harder to debug)",
        ),
    ] = False,
    timeout: Annotated[
        int,
        typer.Option(
            "--timeout",
            help="Timeout in seconds for each example",
        ),
    ] = 30,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Show stdout/stderr for all examples, not just failures",
        ),
    ] = False,
    output: Annotated[
        OutputFormat,
        typer.Option(
            "--output",
            help="Output format: text (default, colored) or json (machine-readable)",
        ),
    ] = OutputFormat.TEXT,
) -> None:
    """Run StreamBlocks examples."""
    try:
        exit_code = asyncio.run(
            main_async(
                category=category,
                skip_api=skip_api,
                include_ui=include_ui,
                dry_run=dry_run,
                parallel=parallel,
                timeout=timeout,
                verbose=verbose,
                output=output,
            )
        )
        raise typer.Exit(code=exit_code)
    except KeyboardInterrupt:
        print_colored("\n\n⚠️  Interrupted by user", "yellow")
        raise typer.Exit(code=130)


if __name__ == "__main__":
    app()
