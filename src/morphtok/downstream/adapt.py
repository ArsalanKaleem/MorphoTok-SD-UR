"""Embedding initialisation when replacing a pretrained model's tokenizer.

Implemented: *decomposition-mean* initialisation -- a new token's embedding is the
mean of the old embeddings of the old tokenizer's pieces for that token's string;
tokens the old tokenizer cannot decompose get a seeded random vector. This is a
generic baseline. Whether it coincides with FVT or with any published method has
**not** been verified; do not describe it under those names.

TODO(literature): verify FOCUS and FVT from their primary sources (method, assumptions,
reference implementation) before implementing or naming them here.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Mapping, Sequence


def decomposition_mean_init(
    new_vocab: Sequence[str],
    old_embeddings: Mapping[str, Sequence[float]],
    old_tokenize: Callable[[str], list[str]],
    dim: int,
    seed: int = 0,
    scale: float = 0.02,
) -> tuple[dict[str, list[float]], dict[str, int]]:
    """Return new embeddings and counts of how each token was initialised."""
    rng = random.Random(seed)
    out: dict[str, list[float]] = {}
    stats = {"copied": 0, "mean": 0, "random": 0}
    for tok in new_vocab:
        if tok in old_embeddings:
            out[tok] = list(old_embeddings[tok])
            stats["copied"] += 1
            continue
        parts = [p for p in old_tokenize(tok) if p in old_embeddings]
        if parts:
            vecs = [old_embeddings[p] for p in parts]
            out[tok] = [sum(v[i] for v in vecs) / len(vecs) for i in range(dim)]
            stats["mean"] += 1
        else:
            out[tok] = [rng.gauss(0.0, scale) for _ in range(dim)]
            stats["random"] += 1
    return out, stats
