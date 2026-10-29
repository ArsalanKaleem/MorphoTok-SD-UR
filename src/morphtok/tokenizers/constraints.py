"""Boundary constraints on a word's segmentation lattice.

Coordinates
-----------
A word of ``n`` characters has *interior boundary positions* ``1 .. n-1``; position
``k`` sits between characters ``k-1`` and ``k``. A segmentation ``s`` induces a set of
present boundaries ``B(s)``. Positions ``0`` and ``n`` are always boundaries and carry
no constraint.

Semantics (documented, not assumed linguistically correct)
----------------------------------------------------------
``MANDATORY``  The boundary must be present. Soft mode: cost ``w`` if absent.
               Hard mode: segmentations without it are excluded.
``PREFERRED``  The boundary is linguistically preferred. Soft mode: cost ``w`` if
               absent. Hard mode: still soft (never an exclusion).
``FORBIDDEN``  The boundary should not be present. Soft mode: cost ``w`` if present.
               Hard mode: segmentations with it are excluded.
``UNKNOWN``    No evidence. Zero cost in every mode. Any position not listed in a
               :class:`WordConstraints` is ``UNKNOWN`` -- absence of analyzer output is
               **never** interpreted as ``FORBIDDEN``.

Here ``w = penalty(confidence)`` in nats, scaled by the global ``lambda`` in the
lattice. Because every cost is attached to a single boundary position, the total
violation cost ``V(s)`` decomposes exactly over lattice edges (see
:meth:`WordConstraints.edge_cost`), so forward/backward/Viterbi remain exact.

Hard-constraint limit
---------------------
With soft costs applied to *exactly the same* set of MANDATORY/FORBIDDEN constraints,
all with confidence > 0, ``V(s) = 0`` iff ``s`` is hard-feasible. As ``lambda -> inf``
the soft posterior converges to the hard posterior *provided the feasible set is
non-empty*. It does **not** converge when: (a) the feasible set is empty (soft
concentrates on minimum-violation segmentations; hard raises), (b) some confidence
maps to zero penalty, or (c) PREFERRED constraints are included in the soft run
(they also become enforced in the limit, but are never hard exclusions).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum


class BoundaryType(StrEnum):
    """Kind of evidence attached to one interior boundary position."""

    MANDATORY = "MANDATORY"
    PREFERRED = "PREFERRED"
    FORBIDDEN = "FORBIDDEN"
    UNKNOWN = "UNKNOWN"


class ConstraintMode(StrEnum):
    """How constraints enter the lattice."""

    NONE = "none"
    SOFT = "soft"
    HARD = "hard"


class InfeasibleConstraintsError(ValueError):
    """Raised when hard constraints leave no valid segmentation in the lattice."""


@dataclass(frozen=True)
class BoundaryConstraint:
    """Evidence about a single interior boundary position."""

    position: int
    kind: BoundaryType
    confidence: float
    source: str = "unspecified"

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")


# ---------------------------------------------------------------------------
# Confidence -> penalty mappings (units: nats, before multiplication by lambda)
# ---------------------------------------------------------------------------

PenaltyFn = Callable[[float], float]


def penalty_linear(confidence: float) -> float:
    """Penalty equal to the confidence itself (bounded in [0, 1])."""
    return confidence


def penalty_log_odds(confidence: float, eps: float = 1e-6) -> float:
    """Positive part of the log-odds; 0 at confidence 0.5, unbounded as c -> 1.

    Clipped at ``eps`` so the result is always finite.
    """
    c = min(max(confidence, eps), 1.0 - eps)
    return max(0.0, math.log(c / (1.0 - c)))


def penalty_threshold(confidence: float, tau: float = 0.5) -> float:
    """Binary: penalty 1 if confidence >= tau else 0 (treats all evidence equally)."""
    return 1.0 if confidence >= tau else 0.0


def penalty_uniform(confidence: float) -> float:
    """Penalty 1 regardless of confidence (the 'unweighted' control for Objective C)."""
    del confidence
    return 1.0


PENALTY_FUNCTIONS: dict[str, PenaltyFn] = {
    "linear": penalty_linear,
    "log_odds": penalty_log_odds,
    "threshold": penalty_threshold,
    "uniform": penalty_uniform,
}


@dataclass
class WordConstraints:
    """All constraints for one word of length ``n`` (in lattice coordinates)."""

    n: int
    constraints: dict[int, BoundaryConstraint] = field(default_factory=dict)
    penalty: str = "linear"

    def __post_init__(self) -> None:
        if self.penalty not in PENALTY_FUNCTIONS:
            raise ValueError(f"unknown penalty mapping {self.penalty!r}")
        for pos in self.constraints:
            if not 0 < pos < self.n:
                raise ValueError(f"constraint position {pos} outside interior 1..{self.n - 1}")
        self._absent_cost: list[float] = [0.0] * (self.n + 1)
        self._present_cost: list[float] = [0.0] * (self.n + 1)
        fn = PENALTY_FUNCTIONS[self.penalty]
        for pos, con in self.constraints.items():
            w = fn(con.confidence)
            if con.kind in (BoundaryType.MANDATORY, BoundaryType.PREFERRED):
                self._absent_cost[pos] = w
            elif con.kind is BoundaryType.FORBIDDEN:
                self._present_cost[pos] = w
        # Prefix sums of absent costs for O(1) edge-cost queries.
        self._absent_prefix: list[float] = [0.0] * (self.n + 2)
        for k in range(1, self.n + 1):
            self._absent_prefix[k + 1] = self._absent_prefix[k] + self._absent_cost[k]

    @classmethod
    def from_iterable(
        cls, n: int, items: Iterable[BoundaryConstraint], penalty: str = "linear"
    ) -> WordConstraints:
        """Build from constraints; later duplicates for a position override earlier ones."""
        return cls(n=n, constraints={c.position: c for c in items}, penalty=penalty)

    @classmethod
    def empty(cls, n: int) -> WordConstraints:
        """No evidence at any position (every position UNKNOWN)."""
        return cls(n=n)

    def kind_at(self, position: int) -> BoundaryType:
        """Return the constraint type at ``position`` (UNKNOWN if none recorded)."""
        con = self.constraints.get(position)
        return con.kind if con is not None else BoundaryType.UNKNOWN

    def edge_cost(self, i: int, j: int) -> float:
        """Violation cost attributable to edge ``[i, j)``.

        Interior positions ``i+1 .. j-1`` are *absent* boundaries; position ``j`` is a
        *present* boundary when ``j < n``. Summing over the edges of a segmentation
        gives exactly ``V(s)``.
        """
        absent = self._absent_prefix[j] - self._absent_prefix[i + 1] if j > i + 1 else 0.0
        present = self._present_cost[j] if j < self.n else 0.0
        return absent + present

    def edge_allowed_hard(self, i: int, j: int) -> bool:
        """Hard feasibility of edge ``[i, j)``: no MANDATORY inside, no FORBIDDEN at end."""
        for k in range(i + 1, j):
            if self.kind_at(k) is BoundaryType.MANDATORY:
                return False
        return not (j < self.n and self.kind_at(j) is BoundaryType.FORBIDDEN)

    def violation_cost(self, boundaries: Iterable[int]) -> float:
        """Total ``V(s)`` for a segmentation given by its interior boundary set."""
        present = set(boundaries)
        total = 0.0
        for k in range(1, self.n):
            total += self._present_cost[k] if k in present else self._absent_cost[k]
        return total

    def is_hard_feasible(self, boundaries: Iterable[int]) -> bool:
        """True iff the boundary set satisfies every MANDATORY and FORBIDDEN constraint."""
        present = set(boundaries)
        for pos, con in self.constraints.items():
            if con.kind is BoundaryType.MANDATORY and pos not in present:
                return False
            if con.kind is BoundaryType.FORBIDDEN and pos in present:
                return False
        return True


def boundaries_of(pieces: Iterable[str]) -> list[int]:
    """Interior boundary positions induced by a list of pieces."""
    out: list[int] = []
    pos = 0
    plist = list(pieces)
    for p in plist[:-1]:
        pos += len(p)
        out.append(pos)
    return out


def validate_segmentation(word: str, pieces: Iterable[str]) -> None:
    """Raise ``ValueError`` unless ``pieces`` is a non-empty-piece partition of ``word``."""
    plist = list(pieces)
    if any(len(p) == 0 for p in plist):
        raise ValueError("segmentation contains an empty piece")
    if "".join(plist) != word:
        raise ValueError(f"pieces {plist!r} do not concatenate to {word!r}")


def constraints_from_mapping(
    n: int,
    kinds: Mapping[int, tuple[BoundaryType, float]],
    penalty: str = "linear",
    source: str = "mapping",
) -> WordConstraints:
    """Convenience constructor: ``{position: (kind, confidence)}``."""
    return WordConstraints.from_iterable(
        n,
        (BoundaryConstraint(p, k, c, source) for p, (k, c) in kinds.items()),
        penalty=penalty,
    )
