"""Cross-platform equivalent of the Makefile targets (for systems without ``make``).

Usage: ``python scripts/make_targets.py <target> [--data synthetic|sindhi|urdu]``.
Added beyond the required tree because the development machine (Windows) has no
``make``; the commands are identical to the Makefile's.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_PY = ROOT / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")

SCRIPTS = {
    "gate0": "scripts/01_baseline_fertility.py",
    "gate1": "scripts/00_zwnj_audit.py",
    "gate2": "scripts/02_analyzer_coverage.py",
    "tokenizer": "scripts/03_train_tokenizers.py",
    "intrinsic": "scripts/04_intrinsic_eval.py",
    "ablations": "scripts/05_ablation_grid.py",
    "lmproxy": "scripts/06_lm_proxy.py",
}


def run(*cmd: str) -> int:
    """Run a command from the repository root, echoing it first."""
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode  # noqa: S603


def main() -> int:
    """Dispatch one target."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", choices=[*SCRIPTS, "setup", "lint", "test", "fixture", "clean", "real-data",
                                       "prereg-status", "prereg-freeze"])  # fmt: skip
    ap.add_argument("--data", default="synthetic")
    ap.add_argument("--config", default="configs/run/default.yaml")
    a = ap.parse_args()
    py = str(VENV_PY) if VENV_PY.exists() else sys.executable
    if a.target in SCRIPTS:
        return run(py, "-X", "utf8", SCRIPTS[a.target], "--config", a.config, "--data", a.data)
    if a.target == "setup":
        if not VENV_PY.exists() and run(sys.executable, "-m", "venv", ".venv"):
            return 1
        py = str(VENV_PY)
        for cmd in (["-m", "pip", "install", "-r", "requirements-dev.lock"],
                    ["-m", "pip", "install", "--no-deps", "-e", "."]):  # fmt: skip
            if run(py, *cmd):
                return 1
        run(py, "-m", "pre_commit", "install")
        return 0
    if a.target == "lint":
        return run(py, "-m", "ruff", "check", ".") or run(py, "-m", "ruff", "format", "--check", ".")
    if a.target == "test":
        return run(py, "-X", "utf8", "-m", "pytest")
    if a.target == "real-data":
        for lang in ("sd", "ur"):
            if run(py, "-X", "utf8", "scripts/prepare_wikipedia.py", lang, "--n-lines", "5000"):
                return 1
            if run(py, "-X", "utf8", "scripts/build_silver.py", lang):
                return 1
        return run(py, "-X", "utf8", "scripts/build_zia_gold.py")
    if a.target == "fixture":
        return run(py, "-X", "utf8", "-m", "morphtok.data.synthetic")
    if a.target == "prereg-status":
        return run(py, "scripts/prereg_freeze.py", "status")
    if a.target == "prereg-freeze":
        return run(py, "scripts/prereg_freeze.py", "freeze")
    if a.target == "clean":
        for d in ("runs", ".pytest_cache", ".ruff_cache"):
            shutil.rmtree(ROOT / d, ignore_errors=True)
        for p in ROOT.rglob("__pycache__"):
            if ".venv" not in p.parts:
                shutil.rmtree(p, ignore_errors=True)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
