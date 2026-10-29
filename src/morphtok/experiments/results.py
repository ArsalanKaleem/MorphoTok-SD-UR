"""Machine-readable result records and the append-only run ledger.

Schema: ``schemas/result.schema.json``. Every attempted run -- including failed and
skipped ones -- is appended to ``runs/ledger.jsonl`` so negative and failed results
cannot silently disappear.
"""

from __future__ import annotations

import json
import re
import traceback
import uuid
from pathlib import Path
from typing import Any

from morphtok import __version__
from morphtok.provenance import environment, git_state, now_utc, prereg_status, stable_hash

RESULT_SCHEMA_VERSION: str = "1.0"
REQUIRED_KEYS: tuple[str, ...] = (
    "schema_version",
    "run_id",
    "experiment_id",
    "status",
    "timestamp",
    "seed",
    "git",
    "prereg",
    "config_hash",
    "data",
    "vocab_size",
    "normalization",
    "tokenizer",
    "environment",
    "metrics",
    "uncertainty",
    "warnings",
    "skipped_steps",
    "synthetic",
)


def new_record(
    experiment_id: str,
    seed: int | None,
    config: dict[str, Any],
    data: dict[str, Any],
    synthetic: bool,
    vocab_size: int | None = None,
    normalization: dict[str, Any] | None = None,
    tokenizer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Start a record with full provenance; ``status`` is 'running' until finalised."""
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "run_id": uuid.uuid4().hex[:12],
        "experiment_id": experiment_id,
        "status": "running",
        "timestamp": now_utc(),
        "seed": seed,
        "git": git_state(),
        "prereg": prereg_status(),
        "config_hash": stable_hash(config),
        "data": data,
        "vocab_size": vocab_size,
        "normalization": normalization or {},
        "tokenizer": tokenizer or {"implementation": "morphtok", "version": __version__},
        "environment": environment(),
        "metrics": {},
        "uncertainty": {},
        "warnings": [],
        "skipped_steps": [],
        "synthetic": synthetic,
        "nondeterminism": [
            "none known for pure-Python components; seeds control corpus subsampling, "
            "bootstrap and sampling-based decoding"
        ],
    }


def validate_record(rec: dict[str, Any]) -> list[str]:
    """Return a list of problems (empty = valid)."""
    problems = [f"missing key {k}" for k in REQUIRED_KEYS if k not in rec]
    if rec.get("status") not in {"ok", "failed", "skipped", "running"}:
        problems.append(f"bad status {rec.get('status')!r}")
    if rec.get("synthetic") is True and not str(rec.get("experiment_id", "")).startswith("SYN"):
        problems.append("synthetic runs must use an experiment_id starting with 'SYN'")
    return problems


def safe_dirname(experiment_id: str) -> str:
    """Filesystem-safe directory name for an experiment ID (portable across OSes)."""
    return re.sub(r"[^A-Za-z0-9._=+-]+", "_", experiment_id).strip("_")


def finalise(
    rec: dict[str, Any], out_dir: Path, status: str = "ok", error: BaseException | None = None
) -> Path:
    """Write the record and append it to the ledger; returns the record path."""
    rec["status"] = status
    if error is not None:
        rec["error"] = "".join(traceback.format_exception(error))[-4000:]
    problems = validate_record(rec)
    if problems:
        rec["warnings"].append(f"record validation problems: {problems}")
    run_dir = out_dir / safe_dirname(rec["experiment_id"])
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / f"{rec['timestamp'].replace(':', '')}_{rec['run_id']}.json"
    path.write_text(json.dumps(rec, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    with (out_dir / "ledger.jsonl").open("a", encoding="utf-8") as fh:
        summary = {k: rec[k] for k in ("run_id", "experiment_id", "status", "timestamp", "seed", "synthetic")}
        summary["path"] = path.relative_to(out_dir).as_posix()
        fh.write(json.dumps(summary, ensure_ascii=False) + "\n")
    return path
