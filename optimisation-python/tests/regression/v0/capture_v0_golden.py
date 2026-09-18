"""WP3-2 capture utility — capture V0 golden responses at demo-opt-base.

Run from the ``optimisation-python`` directory to freeze today's V0 output.
The golden files are committed and checked by ``test_v1_response_golden.py``
and ``test_search_off_golden.py``.

Usage::

    python -m tests.regression.v0.capture_v0_golden [--base demo-opt-base]

Each fixture is posted to ``POST /api/v1/optimise`` with neither C5 flag set,
exactly as the tests do.  Capture refuses to run when the runtime code under
``app/`` differs from ``--base``, so a golden cannot quietly absorb a
behaviour change; re-capturing after an intended change needs a CCR amending
C12 or C2, and ``--base`` set to the commit that carries it.

Each golden records provenance (the base SHA, fixture path and capture
timestamp) so reviewers can verify it was captured at the right commit.
"""

from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys

from tests.regression.v0.v0_harness import (
    FLAGS_UNSET,
    PROVENANCE_KEY,
    ROOT,
    V0_FIXTURES,
    golden_path,
    run_v1,
)

_REPO_ROOT = ROOT.parent


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
        check=False,
    )


def _resolve_base(base: str) -> str:
    """Return the short SHA of ``base``, or exit if app/ differs from it."""
    resolved = _git("rev-parse", "--short", f"{base}^{{commit}}")
    if resolved.returncode != 0:
        sys.exit(f"Cannot resolve base '{base}': {resolved.stderr.strip()}")

    app_dir = (ROOT / "app").relative_to(_REPO_ROOT).as_posix()
    diff = _git("diff", "--quiet", base, "--", app_dir)
    if diff.returncode != 0:
        sys.exit(
            f"Runtime code in {app_dir} differs from {base}; refusing to "
            "capture. V0 goldens must be captured at the base commit."
        )
    return resolved.stdout.strip()


def capture_all(base: str) -> None:
    """Capture golden responses for every V0 fixture."""
    base_sha = _resolve_base(base)
    print(f"Capturing V0 goldens at {base} ({base_sha})")

    for fixture in V0_FIXTURES:
        print(f"  RUN   {fixture.name} ...", end="", flush=True)
        golden = run_v1(fixture, FLAGS_UNSET)
        golden[PROVENANCE_KEY] = {
            "base_sha": base_sha,
            "fixture": fixture.relative_to(ROOT).as_posix(),
            "captured_at": datetime.datetime.now(datetime.UTC).isoformat(),
        }

        path = golden_path(fixture)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(golden, f, indent=2)
            f.write("\n")
        print(f" OK -> {path.relative_to(ROOT).as_posix()}")

    print("Done.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="demo-opt-base")
    capture_all(parser.parse_args().base)


if __name__ == "__main__":
    main()
