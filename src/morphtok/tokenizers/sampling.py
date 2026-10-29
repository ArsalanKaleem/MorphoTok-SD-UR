"""Segmentation sampling and sampling-stability diagnostics (Family E).

All sampling goes through :meth:`Lattice.sample` (forward-filter/backward-sample), so
the samples follow ``P(s | w) proportional to exp(alpha * sum_e phi(e))`` over exactly
the edges present in the lattice (hard exclusions removed, soft costs included).
"""

from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import dataclass

from morphtok.tokenizers.constraints import ConstraintMode, WordConstraints
from morphtok.tokenizers.lattice_unigram import UnigramModel


@dataclass(frozen=True)
class SamplingStats:
    """Stability summary for repeated sampling of one word."""

    n_samples: int
    n_distinct: int
    viterbi_agreement: float
    empirical_entropy: float
    exact_entropy: float


def sample_segmentations(
    model: UnigramModel,
    word: str,
    n: int,
    rng: random.Random,
    alpha: float = 1.0,
    constraints: WordConstraints | None = None,
    lam: float = 0.0,
    mode: ConstraintMode = ConstraintMode.NONE,
) -> list[list[str]]:
    """Draw ``n`` independent segmentations of ``word``."""
    lat = model.lattice(word, constraints, lam, mode, alpha=alpha)
    return [lat.sample(rng) for _ in range(n)]


def sampling_stability(
    model: UnigramModel,
    word: str,
    n: int,
    seed: int,
    alpha: float = 1.0,
    constraints: WordConstraints | None = None,
    lam: float = 0.0,
    mode: ConstraintMode = ConstraintMode.NONE,
) -> SamplingStats:
    """Repeated-sampling stability: distinctness, Viterbi agreement, entropies (nats)."""
    rng = random.Random(seed)
    lat = model.lattice(word, constraints, lam, mode, alpha=alpha)
    samples = [tuple(lat.sample(rng)) for _ in range(n)]
    best, _ = lat.viterbi()
    counts = Counter(samples)
    emp_h = -sum((c / n) * math.log(c / n) for c in counts.values())
    return SamplingStats(
        n_samples=n,
        n_distinct=len(counts),
        viterbi_agreement=counts[tuple(best)] / n,
        empirical_entropy=emp_h,
        exact_entropy=lat.entropy(),
    )
