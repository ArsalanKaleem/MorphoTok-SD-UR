"""Uncertainty estimates and failed-run accounting.

Covers paired bootstrap, approximate randomization, effect sizes, multi-seed
aggregation and Wilson intervals.

Assumptions are stated per function. The bootstrap resamples evaluation *units*
(lines or words) with replacement and assumes units are exchangeable; it does not
account for between-seed variance, which is reported separately by
:func:`aggregate_seeds`.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from typing import Any, TypeVar

U = TypeVar("U")

# Two-sided 95% Student-t critical values t_{0.975, df}, df = 1..30 (standard tables).
_T975 = [
    12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228,
    2.201, 2.179, 2.160, 2.145, 2.131, 2.120, 2.110, 2.101, 2.093, 2.086,
    2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042,
]  # fmt: skip


def t_critical_975(df: int) -> float:
    """``t_{0.975, df}``; for ``df > 30`` returns the df=30 value (slightly conservative)."""
    if df < 1:
        raise ValueError("df must be >= 1")
    return _T975[min(df, 30) - 1]


def percentile(sorted_vals: Sequence[float], q: float) -> float:
    """Linear-interpolated percentile of pre-sorted values, ``q`` in [0, 1]."""
    if not sorted_vals:
        raise ValueError("empty sequence")
    pos = q * (len(sorted_vals) - 1)
    lo, hi = math.floor(pos), math.ceil(pos)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def paired_bootstrap(
    units_a: Sequence[U],
    units_b: Sequence[U],
    statistic: Callable[[Sequence[U]], float],
    n_boot: int = 1000,
    seed: int = 0,
    level: float = 0.95,
) -> dict[str, float]:
    """Bootstrap CI for ``statistic(B) - statistic(A)`` resampling aligned unit indices.

    ``p_two_sided`` is ``2 * min(P*(d <= 0), P*(d >= 0))`` over bootstrap replicates, a
    rough indicator rather than an exact test.
    """
    if len(units_a) != len(units_b):
        raise ValueError("paired units must be aligned")
    n = len(units_a)
    if n == 0:
        raise ValueError("no units")
    rng = random.Random(seed)
    obs = statistic(units_b) - statistic(units_a)
    deltas: list[float] = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        deltas.append(statistic([units_b[i] for i in idx]) - statistic([units_a[i] for i in idx]))
    deltas.sort()
    alpha = (1.0 - level) / 2
    le = sum(1 for d in deltas if d <= 0) / n_boot
    ge = sum(1 for d in deltas if d >= 0) / n_boot
    return {
        "delta": obs,
        "ci_low": percentile(deltas, alpha),
        "ci_high": percentile(deltas, 1 - alpha),
        "p_two_sided": min(1.0, 2 * min(le, ge)),
        "n_units": float(n),
        "n_boot": float(n_boot),
    }


def approximate_randomization(
    units_a: Sequence[U],
    units_b: Sequence[U],
    statistic: Callable[[Sequence[U]], float],
    n_perm: int = 1000,
    seed: int = 0,
) -> dict[str, float]:
    """Paired approximate-randomization test of ``H0: A and B are exchangeable per unit``.

    Valid for any statistic computed from per-unit sufficient statistics (including
    micro F1 and ratio-of-sums fertility). ``p = (#{|d*| >= |d|} + 1) / (n_perm + 1)``.
    """
    if len(units_a) != len(units_b):
        raise ValueError("paired units must be aligned")
    rng = random.Random(seed)
    obs = abs(statistic(units_b) - statistic(units_a))
    hits = 0
    for _ in range(n_perm):
        a2: list[U] = []
        b2: list[U] = []
        for ua, ub in zip(units_a, units_b, strict=True):
            if rng.random() < 0.5:
                a2.append(ub)
                b2.append(ua)
            else:
                a2.append(ua)
                b2.append(ub)
        if abs(statistic(b2) - statistic(a2)) >= obs - 1e-12:
            hits += 1
    return {"abs_delta": obs, "p_value": (hits + 1) / (n_perm + 1), "n_perm": float(n_perm)}


def cohens_dz(diffs: Sequence[float]) -> float | None:
    """Paired effect size ``mean(d) / sd(d)``; ``None`` if undefined (n<2 or sd=0)."""
    n = len(diffs)
    if n < 2:
        return None
    m = sum(diffs) / n
    sd = math.sqrt(sum((d - m) ** 2 for d in diffs) / (n - 1))
    return m / sd if sd > 0 else None


def aggregate_seeds(values: Sequence[float | None]) -> dict[str, Any]:
    """Mean/sd/t-CI over seeds; ``None`` entries are failed runs and are *counted*."""
    ok = [v for v in values if v is not None and math.isfinite(v)]
    out: dict[str, Any] = {"n_seeds": len(values), "n_ok": len(ok), "n_failed": len(values) - len(ok)}
    if not ok:
        return {**out, "mean": None, "sd": None, "ci_low": None, "ci_high": None}
    m = sum(ok) / len(ok)
    if len(ok) < 2:
        return {**out, "mean": m, "sd": None, "ci_low": None, "ci_high": None}
    sd = math.sqrt(sum((v - m) ** 2 for v in ok) / (len(ok) - 1))
    half = t_critical_975(len(ok) - 1) * sd / math.sqrt(len(ok))
    return {**out, "mean": m, "sd": sd, "ci_low": m - half, "ci_high": m + half,
            "min": min(ok), "max": max(ok)}  # fmt: skip


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """Wilson score interval for a binomial proportion; ``None`` if ``n == 0``."""
    if n == 0:
        return None
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)
