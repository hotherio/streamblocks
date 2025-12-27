#!/usr/bin/env python3
"""Manual release script for dev/rc/final releases.

NOTE: The primary release method is automated via python-semantic-release
(see .github/workflows/semantic-release.yml). This script is for manual
releases when you need to create dev or rc versions, or when semantic-release
automation is not appropriate.

Usage:
    python tools/release.py {dev|rc|final} [SHA]

Examples:
    python tools/release.py dev      # Create dev release from HEAD
    python tools/release.py rc       # Create release candidate from HEAD
    python tools/release.py final    # Create final release (uses conventional commits)
"""

import subprocess
import sys

from packaging.version import Version, parse as version_parse


def cmd(c: str) -> str:
    return subprocess.check_output(c, shell=True, text=True).strip()


def last_tag() -> Version:
    try:
        t = cmd("git describe --tags --match='v*' --abbrev=0")
        return version_parse(t.lstrip("v"))
    except subprocess.CalledProcessError:  # no tag yet
        return version_parse("0.0.0")


def rev_list(ref: str) -> list[str]:
    """All commits reachable from ref, newest first."""
    return cmd(f"git rev-list {ref}").splitlines()


def assert_valid_sha(sha: str) -> None:
    """SHA must be reachable from HEAD and not older than last tag."""
    if sha not in rev_list("HEAD"):
        sys.exit(f"{sha} is not reachable from HEAD")
    last = last_tag()
    if last != version_parse("0.0.0"):
        # Check if the sha is already contained in the previous release
        last_tag_sha = cmd(f"git rev-list -n 1 v{last}")
        if sha in rev_list(last_tag_sha):
            sys.exit(f"{sha} is already contained in the previous release {last}")


def needed_bump(sha: str = "HEAD") -> str:
    # Analyze commits to determine bump type
    last = last_tag()
    try:
        if last == version_parse("0.0.0"):
            # No previous tag, analyze all commits up to sha
            out = cmd(f"git-cliff --bump --strip header -- {sha}")
        else:
            # Analyze commits between last tag and sha
            out = cmd(f"git-cliff --bump --strip header v{last}..{sha}")

        # Extract version from output (e.g., "[1.0.3]" -> "1.0.3")
        import re

        match = re.search(r"\[(\d+\.\d+\.\d+)\]", out)
        if match:
            new_version = version_parse(match.group(1))
            # Compare versions to determine bump type
            if new_version.major > last.major:
                return "major"
            if new_version.minor > last.minor:
                return "minor"
            return "patch"
    except Exception:
        pass

    return "patch"  # default if only chores


def next_version(current: Version, stage: str, bump: str) -> str:
    major, minor, patch = current.major, current.minor, current.micro

    # Apply the bump for final releases
    if stage == "final":
        if bump == "major":
            major, minor, patch = major + 1, 0, 0
        elif bump == "minor":
            minor, patch = minor + 1, 0
        elif bump == "patch":
            patch = patch + 1

    # For dev/rc, always increment patch if we're at a final release
    elif not current.is_devrelease and not current.is_prerelease:
        patch = patch + 1

    if stage == "dev":
        # Determine the dev number
        dev_n = 1
        if (
            current.is_devrelease
            and current.major == major
            and current.minor == minor
            and current.micro == patch
            and current.dev is not None
        ):
            dev_n = current.dev + 1
        return f"{major}.{minor}.{patch}-dev{dev_n}"

    if stage == "rc":
        # Determine the rc number
        rc_n = 1
        if (
            current.is_prerelease
            and current.pre is not None
            and current.pre[0] == "rc"
            and current.major == major
            and current.minor == minor
            and current.micro == patch
        ):
            rc_n = current.pre[1] + 1
        return f"{major}.{minor}.{patch}rc{rc_n}"

    # final
    return f"{major}.{minor}.{patch}"


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in {"dev", "rc", "final"}:  # noqa: PLR2004
        sys.exit("usage: hatch release {dev|rc|final} [SHA]")

    stage = sys.argv[1]
    sha = sys.argv[2] if len(sys.argv) >= 3 else "HEAD"  # noqa: PLR2004

    if sha != "HEAD":
        assert_valid_sha(sha)

    current = last_tag()
    bump = needed_bump(sha) if stage == "final" else "patch"  # dev/rc ignore commits
    new = next_version(current, stage, bump)

    print(f"🔖  {current}  →  {new}  (from {sha})")
    cmd(f"git tag -a v{new} {sha} -m 'chore: release v{new}'")
    cmd(f"git push origin v{new}")


if __name__ == "__main__":
    main()
