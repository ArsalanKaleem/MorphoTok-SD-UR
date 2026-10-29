"""Morphological boundary precision / recall / F1 (micro-averaged over words).

For each evaluated word, ``pred`` and ``gold`` are sets of interior boundary positions
in stripped coordinates. Micro-averaging:

* ``TP = sum_w |pred_w & gold_w|``, ``P = TP / sum_w |pred_w|``, ``R = TP / sum_w |gold_w|``;
* ``P`` is ``None`` when no boundary was predicted, ``R`` is ``None`` when gold has
  no boundaries; ``F1`` is ``None`` if either is ``None`` and ``0`` if ``P + R = 0``.

Words without gold boundaries still contribute false positives to ``P``.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class BoundaryCounts:
    """Sufficient statistics for micro P/R/F1."""

    tp: int
    n_pred: int
    n_gold: int

    def __add__(self, other: BoundaryCounts) -> BoundaryCounts:
        return BoundaryCounts(self.tp + other.tp, self.n_pred + other.n_pred, self.n_gold + other.n_gold)


def word_counts(pred: set[int], gold: set[int]) -> BoundaryCounts:
    """Counts for one word."""
    return BoundaryCounts(len(pred & gold), len(pred), len(gold))


def sum_counts(items: Iterable[BoundaryCounts]) -> BoundaryCounts:
    """Sum of per-word counts."""
    total = BoundaryCounts(0, 0, 0)
    for c in items:
        total = total + c
    return total


def prf(c: BoundaryCounts) -> dict[str, float | int | None]:
    """Precision, recall, F1 plus the raw counts."""
    p = c.tp / c.n_pred if c.n_pred else None
    r = c.tp / c.n_gold if c.n_gold else None
    if p is None or r is None:
        f = None
    elif p + r == 0:
        f = 0.0
    else:
        f = 2 * p * r / (p + r)
    return {"precision": p, "recall": r, "f1": f, "tp": c.tp, "n_pred": c.n_pred, "n_gold": c.n_gold}


def boundary_prf(preds: Sequence[set[int]], golds: Sequence[set[int]]) -> dict[str, float | int | None]:
    """Micro P/R/F1 over aligned prediction and gold sets."""
    if len(preds) != len(golds):
        raise ValueError("preds and golds must be aligned")
    return prf(sum_counts(word_counts(p, g) for p, g in zip(preds, golds, strict=True)))


def f1_of_counts(items: Sequence[BoundaryCounts]) -> float:
    """Micro F1 of a collection of word counts, with ``None`` mapped to 0 (for bootstrap)."""
    f = prf(sum_counts(items))["f1"]
    return float(f) if f is not None else 0.0
