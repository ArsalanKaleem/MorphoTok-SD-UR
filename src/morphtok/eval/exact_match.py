"""Exact segmentation accuracy: fraction of words whose boundary set equals gold."""

from __future__ import annotations

from collections.abc import Sequence


def exact_match(preds: Sequence[set[int]], golds: Sequence[set[int]]) -> float | None:
    """``#{w : pred_w == gold_w} / #words``; ``None`` for an empty evaluation set."""
    if len(preds) != len(golds):
        raise ValueError("preds and golds must be aligned")
    if not preds:
        return None
    return sum(1 for p, g in zip(preds, golds, strict=True) if p == g) / len(preds)
