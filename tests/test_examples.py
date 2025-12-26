"""Pytest integration for StreamBlocks examples.

This module provides pytest-based testing for all examples in the streamblocks_examples package.
It's primarily intended for CI/CD pipelines.

Usage:
    pytest tests/test_examples.py                 # Run all examples as tests
    pytest tests/test_examples.py -m "not api"    # Skip API-dependent examples
    pytest tests/test_examples.py -m "not ui"     # Skip UI examples
    pytest tests/test_examples.py -m "not slow"   # Skip slow examples
    pytest tests/test_examples.py -v              # Verbose output
    pytest tests/test_examples.py -n auto         # Parallel execution with pytest-xdist
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

# Get examples directory
EXAMPLES_DIR = Path(__file__).parent.parent / "src" / "hother" / "streamblocks_examples"


def discover_examples() -> list[Path]:
    """Discover all example scripts."""
    examples = []
    for path in EXAMPLES_DIR.rglob("*.py"):
        if path.stem.startswith("_") or path.name == "run_examples.py":
            continue
        # Skip helper directories
        rel_path = path.relative_to(EXAMPLES_DIR)
        if rel_path.parts[0] in ("helpers", "tools", "blocks"):
            continue
        examples.append(path)
    return sorted(examples)


def is_tui_example(path: Path) -> bool:
    """Check if example is a TUI application."""
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        return "from textual" in content or "import textual" in content
    except Exception:
        return False


def detect_api_requirements(path: Path) -> list[str]:
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


def get_category(path: Path) -> str:
    """Get category from folder structure."""
    rel_path = path.relative_to(EXAMPLES_DIR)
    if len(rel_path.parts) > 1:
        return rel_path.parts[0]
    return "root"


def is_slow_example(path: Path) -> bool:
    """Check if example is expected to be slow."""
    # Examples that make actual API calls are slow
    api_keys = detect_api_requirements(path)
    return len(api_keys) > 0


# Generate test IDs based on relative paths
examples = discover_examples()
example_ids = [str(p.relative_to(EXAMPLES_DIR)) for p in examples]


@pytest.mark.parametrize("example_path", examples, ids=example_ids)
def test_example(example_path: Path) -> None:
    """Test that an example runs successfully.

    Args:
        example_path: Path to the example script

    Markers:
        - api: Example requires API keys
        - ui: Example is a TUI application
        - slow: Example is expected to be slow (>5s)
    """
    # Check if TUI
    if is_tui_example(example_path):
        pytest.skip("TUI example - requires interactive user input")

    # Check API requirements
    required_keys = detect_api_requirements(example_path)
    if required_keys:
        # Skip if any required API keys are missing
        missing_keys = [key for key in required_keys if not os.getenv(key)]
        if missing_keys:
            pytest.skip(f"Missing API keys: {', '.join(missing_keys)}")

    # Run the example with src directory in PYTHONPATH for hother.streamblocks imports
    src_dir = str(EXAMPLES_DIR.parent.parent)  # src/hother/streamblocks_examples -> src/
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{src_dir}:{existing_pythonpath}" if existing_pythonpath else src_dir

    result = subprocess.run(
        [sys.executable, str(example_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,  # 60 second timeout for slow examples
        stdin=subprocess.DEVNULL,
        env=env,
    )

    # Check for success
    assert result.returncode == 0, (
        f"Example failed with return code {result.returncode}\n"
        f"stderr: {result.stderr}\n"
        f"stdout: {result.stdout[:500]}"  # First 500 chars
    )

    # Check for exceptions in output
    assert "Traceback" not in result.stderr, f"Exception found in stderr:\n{result.stderr}"


# Marker definitions for pytest
def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "api: Examples that require API keys (Gemini, OpenAI, Anthropic)")
    config.addinivalue_line("markers", "ui: Examples that are TUI applications (Textual)")
    config.addinivalue_line("markers", "slow: Examples that are slow to run (>5s)")


# Collection hook to add markers
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Add markers to test items based on example characteristics."""
    for item in items:
        # Get the example path from the test parameter
        if "example_path" in item.callspec.params:
            example_path: Path = item.callspec.params["example_path"]

            # Add API marker
            if detect_api_requirements(example_path):
                item.add_marker(pytest.mark.api)

            # Add UI marker
            if is_tui_example(example_path):
                item.add_marker(pytest.mark.ui)

            # Add slow marker
            if is_slow_example(example_path):
                item.add_marker(pytest.mark.slow)

            # Add category marker
            category = get_category(example_path)
            item.add_marker(pytest.mark.category(category))


# Fixture to provide summary information
@pytest.fixture(scope="session", autouse=True)
def print_test_info(request: pytest.FixtureRequest) -> None:
    """Print information about test environment."""
    print("\n" + "=" * 70)
    print("StreamBlocks Examples Test Suite")
    print("=" * 70)

    # Check for API keys
    api_keys = {
        "GEMINI_API_KEY": bool(os.getenv("GEMINI_API_KEY")),
        "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
        "ANTHROPIC_API_KEY": bool(os.getenv("ANTHROPIC_API_KEY")),
    }

    print("\nAPI Keys:")
    for key, present in api_keys.items():
        status = "✓ Present" if present else "✗ Missing"
        print(f"  {key}: {status}")

    if not any(api_keys.values()):
        print("\n⚠️  No API keys found - API-dependent examples will be skipped")

    print("=" * 70 + "\n")
