"""Dataset loading with provenance; never substitutes synthetic data for real data.

Real Sindhi/Urdu corpora are not bundled. ``configs/data/{sindhi,urdu}.yaml`` keep
``path: null`` until a corpus with a verified licence is supplied; loading such a
config raises :class:`DataUnavailableError`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT: Path = Path(__file__).resolve().parents[3]
SYNTHETIC_DIR: Path = REPO_ROOT / "tests" / "fixtures" / "synthetic"


class DataUnavailableError(FileNotFoundError):
    """A configured dataset is not present; callers must report, not substitute."""


@dataclass
class DatasetConfig:
    """Parsed ``configs/data/*.yaml``."""

    name: str
    language: str
    synthetic: bool
    corpus_path: str | None
    gold_path: str | None
    zwnj_annotation_path: str | None
    licence: str | None
    domain: str | None
    analyzer: dict[str, Any] = field(default_factory=dict)
    split: dict[str, Any] = field(default_factory=dict)
    paradigms_path: str | None = None

    @classmethod
    def load(cls, path: str | Path) -> DatasetConfig:
        """Read a dataset YAML file."""
        d = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls(
            name=d["name"],
            language=d["language"],
            synthetic=bool(d.get("synthetic", False)),
            corpus_path=d.get("corpus", {}).get("path"),
            gold_path=d.get("gold", {}).get("path"),
            zwnj_annotation_path=d.get("zwnj_annotations", {}).get("path"),
            licence=d.get("corpus", {}).get("licence"),
            domain=d.get("corpus", {}).get("domain"),
            analyzer=d.get("analyzer", {}) or {},
            split=d.get("split", {}) or {},
            paradigms_path=(d.get("paradigms") or {}).get("path"),
        )


def resolve(path: str | None) -> Path | None:
    """Resolve a repo-relative path."""
    if path is None:
        return None
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def sha256_file(path: Path) -> str:
    """Hex SHA-256 of a file's bytes."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_lines(cfg: DatasetConfig) -> tuple[list[str], str]:
    """Return non-empty corpus lines and the corpus SHA-256, or raise."""
    p = resolve(cfg.corpus_path)
    if p is None or not p.exists():
        raise DataUnavailableError(
            f"dataset {cfg.name!r}: corpus path {cfg.corpus_path!r} is not available. "
            "Supply a licensed corpus and set it in the data config. Synthetic data is "
            "NOT substituted."
        )
    text = p.read_text(encoding="utf-8")
    return [ln for ln in text.splitlines() if ln.strip()], sha256_file(p)


@dataclass(frozen=True)
class GoldEntry:
    """One gold segmentation (stripped coordinates)."""

    word: str
    boundaries: tuple[int, ...]
    source: str
    split: str


def load_gold(cfg: DatasetConfig) -> dict[str, GoldEntry]:
    """Load the gold TSV; returns ``{}`` when no gold file is configured or present."""
    p = resolve(cfg.gold_path)
    if p is None or not p.exists():
        return {}
    out: dict[str, GoldEntry] = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        word, bounds, source, split = line.split("\t")
        b = tuple(int(x) for x in bounds.split(",") if x)
        out[word] = GoldEntry(word, b, source, split)
    return out
