"""Abstract morphological-analyzer interface and coverage bookkeeping.

Coordinates: analyzers receive the **format-stripped** canonical word (see
``morphtok.data.normalize``) and return interior boundary positions in that string.

No analyzer in this repository encodes verified Sindhi or Urdu morphology. Real
analyzers must be supplied, and their provenance recorded, before any analyzer-based
result is interpreted linguistically.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum


class CoverageStatus(StrEnum):
    """Whether the analyzer produced an analysis for a word."""

    COVERED = "covered"
    NOT_COVERED = "not_covered"
    ERROR = "error"
    NOT_CONFIGURED = "not_configured"


@dataclass(frozen=True)
class Analysis:
    """One candidate analysis of a word."""

    boundaries: tuple[int, ...]
    confidence: float
    source: str
    version: str
    coverage: CoverageStatus = CoverageStatus.COVERED
    ambiguity: int = 1
    labels: tuple[str, ...] = ()
    notes: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        if list(self.boundaries) != sorted(set(self.boundaries)):
            raise ValueError("boundaries must be strictly increasing")


class AnalyzerNotConfiguredError(RuntimeError):
    """Raised when an analyzer requires a resource that has not been supplied."""


class Analyzer(ABC):
    """``Analyzer.analyze(word) -> list[Analysis]``; empty list means not covered."""

    name: str = "abstract"
    version: str = "0"

    @property
    def is_configured(self) -> bool:
        """Whether a real resource backs this analyzer."""
        return True

    @abstractmethod
    def analyze(self, word: str) -> list[Analysis]:
        """Return zero or more analyses of the format-stripped ``word``."""


class NullAnalyzer(Analyzer):
    """The 'no analyzer' condition (Family C control): covers nothing."""

    name = "null"
    version = "1"

    @property
    def is_configured(self) -> bool:
        """A null analyzer is never a real resource."""
        return False

    def analyze(self, word: str) -> list[Analysis]:
        """Always uncovered."""
        del word
        return []


@dataclass
class CoverageReport:
    """Type- and token-level coverage of an analyzer over a word-frequency table."""

    analyzer: str
    configured: bool
    n_types: int = 0
    n_tokens: int = 0
    covered_types: int = 0
    covered_tokens: int = 0
    error_types: int = 0
    ambiguous_types: int = 0
    examples_uncovered: list[str] = field(default_factory=list)

    @property
    def type_coverage(self) -> float | None:
        """Covered types / all types (``None`` when there are no types)."""
        return self.covered_types / self.n_types if self.n_types else None

    @property
    def token_coverage(self) -> float | None:
        """Covered tokens / all tokens (``None`` when there are no tokens)."""
        return self.covered_tokens / self.n_tokens if self.n_tokens else None


def coverage(
    analyzer: Analyzer, word_counts: Iterable[tuple[str, int]], max_examples: int = 20
) -> CoverageReport:
    """Measure coverage; analyzer exceptions count as ``error`` (never as covered)."""
    rep = CoverageReport(analyzer=analyzer.name, configured=analyzer.is_configured)
    for w, f in word_counts:
        rep.n_types += 1
        rep.n_tokens += f
        try:
            analyses = analyzer.analyze(w)
        except Exception:  # noqa: BLE001 - every failure must be counted, not hidden
            rep.error_types += 1
            continue
        if analyses:
            rep.covered_types += 1
            rep.covered_tokens += f
            if len({a.boundaries for a in analyses}) > 1:
                rep.ambiguous_types += 1
        elif len(rep.examples_uncovered) < max_examples:
            rep.examples_uncovered.append(w)
    return rep
