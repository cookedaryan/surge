#!/usr/bin/env python3
"""Fail a level PR that edits paths it does not own (contract C10).

Usage:
    python scripts/ci/check_ownership.py --level L2 --base demo-opt-base
    python scripts/ci/check_ownership.py --level L2 --paths a.py b.py

A path passes when it matches the level's ``contracts/ownership/L<n>.globs`` and
does not match ``contracts/frozen.txt``. Pattern files hold one glob per line;
``#`` starts a comment; a leading ``!`` excludes paths matched by earlier lines.
``**`` matches across directories and ``*`` within one path segment.

Two files are shared by region, not by path, and pass for both L2 and L3:
``optimisation-python/app/algorithms/wtg_grouping.py``. Reviewers check the region.

Standard library only, so it runs before any project dependency is installed.
"""

import argparse
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OWNERSHIP_DIR = REPO_ROOT / "contracts" / "ownership"
FROZEN_FILE = REPO_ROOT / "contracts" / "frozen.txt"
LEVELS = ("L1", "L2", "L3")


@lru_cache(maxsize=None)
def _compile(glob: str) -> re.Pattern[str]:
    parts: list[str] = []
    index = 0
    while index < len(glob):
        char = glob[index]
        if glob.startswith("**/", index):
            parts.append("(?:.*/)?")
            index += 3
            continue
        if glob.startswith("**", index):
            parts.append(".*")
            index += 2
            continue
        if char == "*":
            parts.append("[^/]*")
        elif char == "?":
            parts.append("[^/]")
        else:
            parts.append(re.escape(char))
        index += 1
    return re.compile("^" + "".join(parts) + "$")


def load_patterns(path: Path) -> list[tuple[bool, str]]:
    patterns = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        negated = line.startswith("!")
        patterns.append((negated, line[1:].strip() if negated else line))
    return patterns


def matches(patterns: list[tuple[bool, str]], path: str) -> bool:
    matched = False
    for negated, glob in patterns:
        if _compile(glob).match(path):
            matched = not negated
    return matched


def violations(level: str, paths: list[str]) -> list[str]:
    owned = load_patterns(OWNERSHIP_DIR / f"{level}.globs")
    frozen = load_patterns(FROZEN_FILE)
    problems = []
    for path in sorted(set(paths)):
        normalised = path.replace("\\", "/")
        if matches(frozen, normalised):
            problems.append(f"{normalised}: frozen (contract change request required)")
        elif not matches(owned, normalised):
            problems.append(f"{normalised}: not owned by {level}")
    return problems


def changed_paths(base: str) -> list[str]:
    output = subprocess.run(
        ["git", "diff", "--name-status", "-M", f"{base}...HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    paths = []
    for line in output.splitlines():
        fields = line.split("\t")
        # Renames and copies list both the old and new path; both must be owned.
        paths.extend(fields[1:])
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", required=True, choices=LEVELS)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--base")
    source.add_argument("--paths", nargs="+")
    args = parser.parse_args()
    paths = args.paths if args.paths else changed_paths(args.base)
    problems = violations(args.level, paths)
    if problems:
        print(f"Ownership check failed for {args.level}:")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print(f"Ownership check passed for {args.level} ({len(set(paths))} paths).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
