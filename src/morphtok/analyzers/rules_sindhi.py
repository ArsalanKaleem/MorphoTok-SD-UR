"""Generic affix-rule engine intended for a Sindhi rule set -- shipped with NO rules.

The engine is language-neutral: it matches prefix/suffix strings supplied in a YAML
file and proposes boundaries. This repository does not include any Sindhi affix list
because none has been supplied or verified. Every rule must carry provenance
(``source``) and a reviewer-assigned ``confidence``; rules without provenance are
rejected at load time.

Rule file format (``configs/data/sindhi.yaml: analyzer.rules_path``)::

    version: "<identifier>"
    rules:
      - kind: suffix          # or prefix
        affix: "<string>"
        min_stem_len: 2
        confidence: 0.8
        source: "<citation or reviewer id>"

TODO(resource): obtain a verified Sindhi affix inventory and reviewer sign-off.
TODO(science): affix stripping over-segments (e.g. stems ending in affix-like
strings); measure precision on the manually reviewed subset before use (Gate 2).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from morphtok.analyzers.base import Analysis, Analyzer, AnalyzerNotConfiguredError


@dataclass(frozen=True)
class AffixRule:
    """One prefix or suffix rule with provenance."""

    kind: str
    affix: str
    min_stem_len: int
    confidence: float
    source: str

    def boundary(self, word: str) -> int | None:
        """Boundary position proposed by this rule, if it applies."""
        if not self.affix:
            return None
        if self.kind == "suffix" and word.endswith(self.affix):
            pos = len(word) - len(self.affix)
            return pos if pos >= self.min_stem_len else None
        if self.kind == "prefix" and word.startswith(self.affix):
            pos = len(self.affix)
            return pos if len(word) - pos >= self.min_stem_len else None
        return None


def load_rules(path: str | Path) -> tuple[str, list[AffixRule]]:
    """Load and validate a rule file; raises on missing provenance."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    version = str(data.get("version", "unversioned"))
    rules: list[AffixRule] = []
    for i, r in enumerate(data.get("rules", [])):
        if not r.get("source"):
            raise ValueError(f"rule {i} has no 'source' provenance; refusing to load")
        if r.get("kind") not in {"prefix", "suffix"}:
            raise ValueError(f"rule {i}: kind must be prefix or suffix")
        rules.append(
            AffixRule(
                kind=r["kind"],
                affix=str(r["affix"]),
                min_stem_len=int(r.get("min_stem_len", 2)),
                confidence=float(r["confidence"]),
                source=str(r["source"]),
            )
        )
    return version, rules


class SindhiRuleAnalyzer(Analyzer):
    """Applies every matching rule; each matching rule yields one single-boundary analysis.

    Combining several affixes into one analysis (stacked suffixes) is intentionally
    not attempted until a verified rule set defines ordering constraints.
    """

    name = "sindhi_rules"

    def __init__(self, rules_path: str | Path | None = None) -> None:
        self.rules: list[AffixRule] = []
        self.version = "none"
        if rules_path is not None and Path(rules_path).exists():
            self.version, self.rules = load_rules(rules_path)

    @property
    def is_configured(self) -> bool:
        """True only when at least one provenance-bearing rule is loaded."""
        return bool(self.rules)

    def analyze(self, word: str) -> list[Analysis]:
        """Return one analysis per applicable rule."""
        if not self.is_configured:
            raise AnalyzerNotConfiguredError("no Sindhi rule file configured")
        out: list[Analysis] = []
        for rule in self.rules:
            b = rule.boundary(word)
            if b is not None and 0 < b < len(word):
                out.append(
                    Analysis(
                        boundaries=(b,),
                        confidence=rule.confidence,
                        source=f"{self.name}:{rule.source}",
                        version=self.version,
                        labels=(f"{rule.kind}:{rule.affix}",),
                    )
                )
        n = len({a.boundaries for a in out})
        return [Analysis(**{**a.__dict__, "ambiguity": n}) for a in out]
