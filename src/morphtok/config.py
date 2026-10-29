"""YAML configuration loading and resolution.

A run config (``configs/run/*.yaml``) names a dataset config, tokenizer configs and an
eval config by path; :func:`load_run_config` resolves them into one mapping whose
:func:`morphtok.provenance.stable_hash` is the run's configuration hash.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from morphtok.provenance import REPO_ROOT


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Read a YAML mapping (repo-relative paths allowed)."""
    p = Path(path)
    if not p.is_absolute():
        p = REPO_ROOT / p
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{p} does not contain a mapping")
    return data


def load_run_config(path: str | Path, dataset_override: str | None = None) -> dict[str, Any]:
    """Resolve a run config and every config it references."""
    run = load_yaml(path)
    data_path = dataset_override or run["data"]
    if not str(data_path).endswith(".yaml"):
        data_path = f"configs/data/{data_path}.yaml"
    resolved = dict(run)
    resolved["data_config_path"] = str(data_path)
    resolved["data_cfg"] = load_yaml(data_path)
    resolved["tokenizer_cfgs"] = {
        name: load_yaml(f"configs/tokenizer/{name}.yaml") for name in run["tokenizers"]
    }
    resolved["eval_cfg"] = load_yaml(run.get("eval", "configs/eval/intrinsic.yaml"))
    return resolved
