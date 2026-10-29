"""From analyzer analyses to lattice constraints; perturbation and calibration tools.

Aggregation of ambiguous analyses (a documented modelling choice, not a fact):
analyses of one word are treated as *alternatives* weighted by their confidences
``c_a``. The support for boundary ``k`` is ``p_k = sum_{a: k in a} c_a / sum_a c_a`` and
the reliability of the word's evidence is ``r = max_a c_a``; the boundary confidence is
``r * p_k``. TODO(science): replace with a calibrated estimate once Gate 2 provides
manually reviewed boundaries (see :func:`calibration_table`).

Positions never proposed for a *covered* word are ``UNKNOWN`` by default. Treating
them as ``FORBIDDEN`` is available only as an explicit, separately named condition
(``covered_absent: forbidden``), because absence of evidence is not evidence of
absence.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from morphtok.analyzers.base import Analysis, Analyzer
from morphtok.data.normalize import ProcessedWord
from morphtok.tokenizers.constraints import BoundaryConstraint, BoundaryType, WordConstraints


@dataclass(frozen=True)
class SupervisionConfig:
    """How analyzer evidence becomes constraints (Family C / Objective C)."""

    proposed_kind: BoundaryType = BoundaryType.MANDATORY
    min_confidence: float = 0.0
    penalty: str = "linear"
    covered_absent: str = "unknown"
    covered_absent_confidence: float = 0.0
    format_char_attach: str = "left"

    @classmethod
    def from_dict(cls, d: Mapping[str, object]) -> SupervisionConfig:
        """Build from a YAML mapping."""
        return cls(
            proposed_kind=BoundaryType(str(d.get("proposed_kind", "MANDATORY"))),
            min_confidence=float(d.get("min_confidence", 0.0)),  # type: ignore[arg-type]
            penalty=str(d.get("penalty", "linear")),
            covered_absent=str(d.get("covered_absent", "unknown")),
            covered_absent_confidence=float(d.get("covered_absent_confidence", 0.0)),  # type: ignore[arg-type]
            format_char_attach=str(d.get("format_char_attach", "left")),
        )


def aggregate(analyses: Iterable[Analysis]) -> dict[int, float]:
    """Per-position boundary confidence in stripped coordinates (see module docstring)."""
    alist = [a for a in analyses if a.confidence > 0.0]
    if not alist:
        return {}
    total = sum(a.confidence for a in alist)
    r = max(a.confidence for a in alist)
    support: dict[int, float] = {}
    for a in alist:
        for k in a.boundaries:
            support[k] = support.get(k, 0.0) + a.confidence
    return {k: r * s / total for k, s in support.items()}


def _stripped_to_processed(pw: ProcessedWord, attach: str) -> dict[int, int]:
    """Map stripped positions to one processed position (format chars attach left/right)."""
    out: dict[int, int] = {}
    for p, s in enumerate(pw.to_stripped):
        if attach == "left":
            out[s] = p  # last processed position wins -> boundary after the format run
        elif s not in out:
            out[s] = p
    return out


def constraints_for_word(
    pw: ProcessedWord,
    analyses: list[Analysis] | None,
    cfg: SupervisionConfig,
) -> list[WordConstraints | None]:
    """One ``WordConstraints`` (or ``None`` = no evidence) per pre-token piece of ``pw``."""
    if not analyses:
        return [None] * len(pw.pieces)
    conf = aggregate(analyses)
    s2p = _stripped_to_processed(pw, cfg.format_char_attach)
    n_stripped = pw.to_stripped[-1]
    full: dict[int, BoundaryConstraint] = {}
    for k in range(1, n_stripped):
        p = s2p.get(k)
        if p is None:
            continue
        c = conf.get(k)
        if c is not None and c >= cfg.min_confidence:
            full[p] = BoundaryConstraint(p, cfg.proposed_kind, c, "analyzer")
        elif c is None and cfg.covered_absent == "forbidden":
            full[p] = BoundaryConstraint(
                p, BoundaryType.FORBIDDEN, cfg.covered_absent_confidence, "covered_absent"
            )
    out: list[WordConstraints | None] = []
    offset = 0
    for piece in pw.pieces:
        local = {
            pos - offset: BoundaryConstraint(pos - offset, c.kind, c.confidence, c.source)
            for pos, c in full.items()
            if offset < pos < offset + len(piece)
        }
        out.append(WordConstraints(len(piece), local, cfg.penalty) if local else None)
        offset += len(piece)
    return out


class PerturbedAnalyzer(Analyzer):
    """Wraps any analyzer to reduce coverage or corrupt boundaries (robustness tests)."""

    def __init__(
        self,
        inner: Analyzer,
        coverage: float = 1.0,
        p_delete: float = 0.0,
        p_insert: float = 0.0,
        seed: int = 0,
    ) -> None:
        self.inner = inner
        self.coverage = coverage
        self.p_delete = p_delete
        self.p_insert = p_insert
        self.seed = seed
        self.name = f"perturbed({inner.name})"
        self.version = f"{inner.version}+cov{coverage}+del{p_delete}+ins{p_insert}+s{seed}"

    @property
    def is_configured(self) -> bool:
        """Configured iff the wrapped analyzer is."""
        return self.inner.is_configured

    def analyze(self, word: str) -> list[Analysis]:
        """Deterministically perturbed analyses of the inner analyzer."""
        h = hashlib.sha256(f"{self.seed}|cov|{word}".encode()).digest()
        if int.from_bytes(h[:8], "big") / 2**64 >= self.coverage:
            return []
        rng = random.Random(f"{self.seed}|{word}")
        out: list[Analysis] = []
        for a in self.inner.analyze(word):
            kept = {b for b in a.boundaries if rng.random() >= self.p_delete}
            kept |= {k for k in range(1, len(word)) if rng.random() < self.p_insert}
            out.append(Analysis(**{**a.__dict__, "boundaries": tuple(sorted(kept))}))
        return out


class RandomBoundaryAnalyzer(Analyzer):
    """Negative control: same coverage and boundary *count* as ``inner``, random positions.

    If a method gains as much from this control as from the real analyzer, the gain is
    not due to morphological information (e.g. it is a generic "more boundaries" effect).
    """

    def __init__(self, inner: Analyzer, seed: int = 0) -> None:
        self.inner = inner
        self.seed = seed
        self.name = f"random_control({inner.name})"
        self.version = f"{inner.version}+random{seed}"

    @property
    def is_configured(self) -> bool:
        """Configured iff the wrapped analyzer is."""
        return self.inner.is_configured

    def analyze(self, word: str) -> list[Analysis]:
        """Replace each analysis's boundaries by a random set of equal size."""
        rng = random.Random(f"{self.seed}|rand|{word}")
        out: list[Analysis] = []
        for a in self.inner.analyze(word):
            k = min(len(a.boundaries), max(0, len(word) - 1))
            b = tuple(sorted(rng.sample(range(1, len(word)), k))) if k else ()
            out.append(Analysis(**{**a.__dict__, "boundaries": b, "source": f"RANDOM({a.source})"}))
        return out


def calibration_table(
    predicted: Mapping[str, Mapping[int, float]],
    gold: Mapping[str, Iterable[int]],
    n_bins: int = 10,
) -> dict[str, object]:
    """Reliability of boundary confidences against gold boundaries.

    Only words present in both mappings are used; within those, every position the
    analyzer assigned a confidence is a prediction. Returns per-bin counts, accuracy,
    and expected calibration error (ECE). Positions the analyzer never proposed are
    not scored here (they are recall errors, reported by boundary metrics).
    """
    bins = [[0, 0.0, 0.0] for _ in range(n_bins)]  # count, sum_conf, sum_correct
    for w, confs in predicted.items():
        if w not in gold:
            continue
        g = set(gold[w])
        for k, c in confs.items():
            b = min(int(c * n_bins), n_bins - 1)
            bins[b][0] += 1
            bins[b][1] += c
            bins[b][2] += 1.0 if k in g else 0.0
    total = sum(b[0] for b in bins)
    ece = 0.0
    rows = []
    for i, (cnt, sc, sk) in enumerate(bins):
        if cnt:
            ece += (cnt / total) * abs(sk / cnt - sc / cnt)
        rows.append(
            {
                "bin": i,
                "count": cnt,
                "mean_conf": sc / cnt if cnt else None,
                "accuracy": sk / cnt if cnt else None,
            }
        )
    return {"n": total, "ece": ece if total else None, "bins": rows}
