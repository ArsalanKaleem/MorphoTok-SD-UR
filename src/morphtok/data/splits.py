"""Deterministic, content-hashed data splits and leakage checks.

Lines are assigned to splits by a salted hash of their *content*, so exact duplicate
lines always fall in the same split (prevents the most common leakage). Gold word
types are split dev/test by type, so a word used for tuning never appears in the
reported test set.

TODO(data): for real corpora with document IDs, split by document, not by line;
near-duplicate detection is not implemented.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Iterable, Mapping, Sequence


def _unit(salt: str, key: str) -> float:
    h = hashlib.sha256(f"{salt}|{key}".encode()).digest()
    return int.from_bytes(h[:8], "big") / 2**64


def split_lines(
    lines: Sequence[str], ratios: Mapping[str, float], salt: str = "morphtok"
) -> dict[str, list[str]]:
    """Assign each line to a split with probability proportional to ``ratios``."""
    total = sum(ratios.values())
    if total <= 0:
        raise ValueError("ratios must sum to a positive number")
    names = list(ratios)
    cuts: list[float] = []
    acc = 0.0
    for n in names:
        acc += ratios[n] / total
        cuts.append(acc)
    out: dict[str, list[str]] = {n: [] for n in names}
    for line in lines:
        u = _unit(salt, line)
        for n, c in zip(names, cuts, strict=True):
            if u < c:
                out[n].append(line)
                break
        else:
            out[names[-1]].append(line)
    return out


def subsample(lines: Sequence[str], fraction: float, seed: int) -> list[str]:
    """Seeded subsample used as the source of between-seed variation in training."""
    if not 0.0 < fraction <= 1.0:
        raise ValueError("fraction must be in (0, 1]")
    if fraction == 1.0:
        return list(lines)
    rng = random.Random(seed)
    return [ln for ln in lines if rng.random() < fraction]


def check_disjoint(a: Iterable[str], b: Iterable[str]) -> set[str]:
    """Return the overlap between two collections (empty set = no leakage)."""
    return set(a) & set(b)
