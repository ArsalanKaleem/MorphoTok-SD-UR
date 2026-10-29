"""Frequency-stratified and coverage-stratified evaluation.

Strata are defined by the **training-corpus** frequency of the stripped word type,
so "unseen" means absent from the tokenizer's training data. Bin edges come from
``configs/eval/intrinsic.yaml`` and must be fixed before looking at test results.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import TypeVar

from morphtok.eval.exact_match import exact_match
from morphtok.eval.morph_boundary import boundary_prf

T = TypeVar("T")


def frequency_bin(freq: int, edges: Sequence[int]) -> str:
    """Label for ``freq`` given ascending upper bin edges.

    Example: edges ``[0, 1, 5]`` give labels ``"0"``, ``"1"``, ``"2-5"`` and ``">5"``.
    """
    lo = 0
    for e in edges:
        if freq <= e:
            return str(e) if lo == e else f"{lo}-{e}"
        lo = e + 1
    return f">{edges[-1]}" if edges else "all"


def stratify(keys: Sequence[str], *aligned: Sequence[T]) -> dict[str, tuple[list[T], ...]]:
    """Group aligned sequences by a key per item."""
    out: dict[str, tuple[list[T], ...]] = {}
    for i, k in enumerate(keys):
        bucket = out.setdefault(k, tuple([] for _ in aligned))
        for seq, b in zip(aligned, bucket, strict=True):
            b.append(seq[i])
    return out


def stratified_boundary_metrics(
    words: Sequence[str],
    preds: Sequence[set[int]],
    golds: Sequence[set[int]],
    key: Callable[[str], str],
) -> dict[str, dict[str, object]]:
    """Boundary P/R/F1 and exact match per stratum, with stratum sizes."""
    groups = stratify([key(w) for w in words], preds, golds)
    out: dict[str, dict[str, object]] = {}
    for k, (p, g) in sorted(groups.items()):
        out[k] = {"n_words": len(p), **boundary_prf(p, g), "exact_match": exact_match(p, g)}
    return out


def frequency_key(train_counts: Mapping[str, int], edges: Sequence[int]) -> Callable[[str], str]:
    """Key function: training-frequency bin of a word."""
    return lambda w: frequency_bin(train_counts.get(w, 0), edges)
