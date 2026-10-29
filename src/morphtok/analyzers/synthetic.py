"""SYNTHETIC-ONLY oracle analyzer for integration tests and robustness demos.

Reads the generator's ground-truth segmentation of the synthetic corpus and returns
it, optionally degraded (reduced coverage, boundary deletion/insertion/shift,
confidence noise). It must never be configured for Sindhi or Urdu data; the run
scripts refuse to combine it with a non-synthetic dataset.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Mapping
from dataclasses import dataclass

from morphtok.analyzers.base import Analysis, Analyzer


def _unit_hash(*parts: object) -> float:
    h = hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).digest()
    return int.from_bytes(h[:8], "big") / 2**64


@dataclass
class SyntheticOracleAnalyzer(Analyzer):
    """Oracle with controllable degradation; all randomness is a hash of (seed, word)."""

    gold: Mapping[str, tuple[int, ...]]
    coverage: float = 1.0
    p_delete: float = 0.0
    p_insert: float = 0.0
    p_shift: float = 0.0
    confidence: float = 0.9
    confidence_noise: float = 0.0
    seed: int = 0
    name: str = "synthetic_oracle"
    version: str = "synthetic-1"

    def analyze(self, word: str) -> list[Analysis]:
        """Degraded gold analysis, or ``[]`` if not in gold / dropped from coverage."""
        if word not in self.gold or _unit_hash(self.seed, "cov", word) >= self.coverage:
            return []
        rng = random.Random(f"{self.seed}|{word}")
        out: set[int] = set()
        for b in self.gold[word]:
            if rng.random() < self.p_delete:
                continue
            if rng.random() < self.p_shift:
                b = b + rng.choice((-1, 1))
            if 0 < b < len(word):
                out.add(b)
        for k in range(1, len(word)):
            if k not in out and rng.random() < self.p_insert:
                out.add(k)
        conf = self.confidence + rng.uniform(-self.confidence_noise, self.confidence_noise)
        conf = min(1.0, max(0.0, conf))
        return [
            Analysis(
                boundaries=tuple(sorted(out)),
                confidence=conf,
                source="SYNTHETIC",
                version=self.version,
            )
        ]
