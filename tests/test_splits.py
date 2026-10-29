"""Deterministic splits, leakage checks, and missing-data behaviour."""

from __future__ import annotations

import pytest

from morphtok.data.loaders import DatasetConfig, DataUnavailableError, load_lines
from morphtok.data.splits import check_disjoint, split_lines, subsample
from morphtok.provenance import REPO_ROOT


def test_split_deterministic_and_complete() -> None:
    lines = [f"line {i}" for i in range(500)]
    a = split_lines(lines, {"train": 0.8, "dev": 0.1, "test": 0.1}, salt="s")
    b = split_lines(lines, {"train": 0.8, "dev": 0.1, "test": 0.1}, salt="s")
    assert a == b
    assert sum(len(v) for v in a.values()) == 500
    assert not check_disjoint(a["train"], a["test"])
    assert 300 < len(a["train"]) < 480


def test_duplicates_never_straddle_splits() -> None:
    lines = ["dup"] * 50 + [f"u{i}" for i in range(50)]
    s = split_lines(lines, {"train": 0.5, "test": 0.5})
    homes = [k for k, v in s.items() if "dup" in v]
    assert len(homes) == 1


def test_salt_changes_assignment() -> None:
    lines = [f"l{i}" for i in range(200)]
    assert split_lines(lines, {"a": 0.5, "b": 0.5}, "x") != split_lines(lines, {"a": 0.5, "b": 0.5}, "y")


def test_subsample() -> None:
    lines = [str(i) for i in range(1000)]
    assert subsample(lines, 1.0, 0) == lines
    s0, s1 = subsample(lines, 0.5, 0), subsample(lines, 0.5, 1)
    assert s0 != s1 and s0 == subsample(lines, 0.5, 0)
    with pytest.raises(ValueError):
        subsample(lines, 0.0, 0)


def test_real_datasets_are_not_substituted() -> None:
    import dataclasses

    for name in ("sindhi", "urdu"):
        cfg = DatasetConfig.load(REPO_ROOT / "configs" / "data" / f"{name}.yaml")
        assert cfg.synthetic is False
        # a missing or unset corpus must raise, never fall back to synthetic data
        for path in (None, "data/raw/does_not_exist.txt"):
            with pytest.raises(DataUnavailableError):
                load_lines(dataclasses.replace(cfg, corpus_path=path))


def test_synthetic_gold_dev_test_disjoint() -> None:
    from morphtok.data.loaders import load_gold

    cfg = DatasetConfig.load(REPO_ROOT / "configs" / "data" / "synthetic.yaml")
    gold = load_gold(cfg)
    dev = {w for w, e in gold.items() if e.split == "dev"}
    test = {w for w, e in gold.items() if e.split == "test"}
    assert dev and test and not (dev & test)
