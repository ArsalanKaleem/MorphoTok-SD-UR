"""Run provenance: git state, preregistration status, environment, hashes.

Nothing here *claims* a state; every field is measured at run time. If git is
unavailable the fields are ``None`` and a warning is recorded.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

REPO_ROOT: Path = Path(__file__).resolve().parents[2]
PREREG_TAG_PREFIX: str = "prereg-v"
PREREG_FILES: tuple[str, ...] = (
    "prereg/PREREG.md",
    "prereg/claim_ledger.md",
    "prereg/decision_gates.md",
)


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip()


def git_state() -> dict[str, Any]:
    """Commit hash (``None`` if no commit), dirty flag, branch."""
    inside = _git("rev-parse", "--is-inside-work-tree")
    if inside != "true":
        return {"commit": None, "dirty": None, "branch": None, "warning": "not a git repository"}
    commit = _git("rev-parse", "HEAD")
    status = _git("status", "--porcelain")
    return {
        "commit": commit,
        "dirty": bool(status) if status is not None else None,
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "warning": None if commit else "repository has no commits",
    }


def prereg_hash() -> str:
    """SHA-256 over the preregistration files' bytes (in fixed order)."""
    h = hashlib.sha256()
    for rel in PREREG_FILES:
        p = REPO_ROOT / rel
        h.update(rel.encode())
        h.update(p.read_bytes() if p.exists() else b"<missing>")
    return h.hexdigest()


def prereg_status() -> dict[str, Any]:
    """Whether a ``prereg-v*`` tag exists and whether prereg files changed since it.

    ``frozen`` is True only if a tag exists **and** the tagged prereg files equal the
    working-tree files. Anything else is reported as not frozen.
    """
    tags_out = _git("tag", "--list", f"{PREREG_TAG_PREFIX}*")
    if tags_out is None:
        return {"frozen": False, "tag": None, "reason": "git unavailable"}
    tags = sorted(t for t in tags_out.splitlines() if t)
    if not tags:
        return {"frozen": False, "tag": None, "reason": "no prereg tag"}
    tag = tags[-1]
    changed = _git("diff", "--name-only", tag, "--", *PREREG_FILES)
    if changed is None:
        return {"frozen": False, "tag": tag, "reason": "could not diff against tag"}
    return {
        "frozen": not changed,
        "tag": tag,
        "reason": None if not changed else f"prereg files changed since {tag}: amendments required",
    }


def environment() -> dict[str, Any]:
    """Python, platform, hardware, and versions of key packages."""
    pkgs = {}
    for name in ("pyyaml", "pytest", "ruff", "numpy", "torch", "sentencepiece", "tokenizers"):
        try:
            pkgs[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            pkgs[name] = None
    return {
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "cpu_count": os.cpu_count(),
        "packages": pkgs,
        "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
    }


def stable_hash(obj: Any) -> str:
    """SHA-256 of canonical JSON (sorted keys) of ``obj``."""
    blob = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def now_utc() -> str:
    """ISO-8601 UTC timestamp."""
    return datetime.now(UTC).isoformat(timespec="seconds")
