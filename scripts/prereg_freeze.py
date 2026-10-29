"""Freeze or inspect the preregistration (git tag ``prereg-vN``).

``status``  prints whether a freeze tag exists and whether prereg files changed since it.
``freeze``  refuses unless the working tree is clean and HEAD exists, then creates an
            annotated tag ``prereg-v<N+1>`` whose message contains the prereg hash.

The script never claims a freeze it has not verified: ``status`` re-checks git state.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from morphtok.provenance import (
    PREREG_TAG_PREFIX,
    REPO_ROOT,
    git_state,
    prereg_hash,
    prereg_status,
)


def main() -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=["status", "freeze"])
    args = ap.parse_args()
    st = prereg_status()
    if args.action == "status":
        print(f"frozen: {st['frozen']}  tag: {st['tag']}  note: {st['reason']}")
        print(f"current prereg hash: {prereg_hash()}")
        return 0
    g = git_state()
    if g["commit"] is None:
        print(f"Refusing to freeze: {g['warning']}")
        return 1
    if g["dirty"]:
        print("Refusing to freeze: working tree has uncommitted changes.")
        return 1
    if st["frozen"]:
        print(
            f"Already frozen at {st['tag']}; record changes in prereg/AMENDMENTS.md and re-freeze after edits."
        )
        return 1
    n = int(st["tag"][len(PREREG_TAG_PREFIX) :]) + 1 if st["tag"] else 1
    tag = f"{PREREG_TAG_PREFIX}{n}"
    msg = f"Preregistration freeze {tag}\nprereg sha256: {prereg_hash()}\ncommit: {g['commit']}"
    subprocess.run(["git", "tag", "-a", tag, "-m", msg], cwd=REPO_ROOT, check=True)  # noqa: S603,S607
    print(f"created tag {tag}; verify with: python scripts/prereg_freeze.py status")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
