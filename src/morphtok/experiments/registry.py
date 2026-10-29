"""Experiment registry: every experiment is a documented, falsifiable specification.

Added beyond the required tree (Part III requires an experiment abstraction). Specs
live in ``configs/experiments/registry.yaml``; this module loads and validates them.
A spec is *rejected* if it does not answer the six mandatory questions:

1. ``uncertainty``          -- what uncertainty are we resolving?
2. ``competing_explanations`` -- what competing explanations exist?
3. ``distinguishing_observation`` -- what observation distinguishes them?
4. ``controlled``           -- what variables must remain fixed?
5. ``abandon_if``           -- what result makes us abandon the hypothesis?
6. ``followups``            -- which follow-up is justified by each possible result?
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from morphtok.provenance import REPO_ROOT

DESIGNS: frozenset[str] = frozenset(
    {"factorial", "ofat", "paired", "sensitivity", "negative_control", "audit"}
)
REQUIRED_TEXT: tuple[str, ...] = (
    "uncertainty",
    "distinguishing_observation",
    "abandon_if",
    "intervention",
    "primary_metric",
)


class SpecError(ValueError):
    """Raised for an incomplete or inconsistent experiment specification."""


@dataclass
class ExperimentSpec:
    """One registered experiment."""

    exp_id: str
    family: str
    hypothesis: str
    gate: int
    design: str
    uncertainty: str
    competing_explanations: list[str]
    distinguishing_observation: str
    controlled: list[str]
    nuisance: list[str]
    baselines: list[str]
    intervention: str
    primary_metric: str
    secondary_metrics: list[str]
    seeds: list[int]
    expected_outcomes: dict[str, str]
    falsification: str
    abandon_if: str
    followups: dict[str, str]
    resources: dict[str, Any] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    config: str | None = None
    status: str = "registered"

    def validate(self) -> None:
        """Raise :class:`SpecError` unless all mandatory questions are answered."""
        missing = [k for k in REQUIRED_TEXT if not str(getattr(self, k)).strip()]
        if missing:
            raise SpecError(f"{self.exp_id}: empty fields {missing}")
        if len(self.competing_explanations) < 2:
            raise SpecError(f"{self.exp_id}: need >= 2 competing explanations")
        if not self.controlled:
            raise SpecError(f"{self.exp_id}: no controlled variables listed")
        if set(self.expected_outcomes) != set(self.competing_explanations):
            raise SpecError(f"{self.exp_id}: expected_outcomes must cover each explanation exactly")
        if not self.followups:
            raise SpecError(f"{self.exp_id}: no follow-up decisions")
        if self.design not in DESIGNS:
            raise SpecError(f"{self.exp_id}: unknown design {self.design!r}")
        if not self.falsification.strip():
            raise SpecError(f"{self.exp_id}: no falsification condition")


class Registry:
    """In-memory registry with uniqueness and validation guarantees."""

    def __init__(self) -> None:
        self._specs: dict[str, ExperimentSpec] = {}

    def register(self, spec: ExperimentSpec) -> None:
        """Validate and add; IDs are unique."""
        spec.validate()
        if spec.exp_id in self._specs:
            raise SpecError(f"duplicate experiment id {spec.exp_id}")
        self._specs[spec.exp_id] = spec

    def get(self, exp_id: str) -> ExperimentSpec:
        """Look up a spec."""
        return self._specs[exp_id]

    def by_family(self, family: str) -> list[ExperimentSpec]:
        """All specs in a family, in ID order."""
        return sorted((s for s in self._specs.values() if s.family == family), key=lambda s: s.exp_id)

    def by_gate(self, gate: int) -> list[ExperimentSpec]:
        """All specs attached to a decision gate."""
        return sorted((s for s in self._specs.values() if s.gate == gate), key=lambda s: s.exp_id)

    def __len__(self) -> int:
        return len(self._specs)

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(sorted(self._specs.values(), key=lambda s: s.exp_id))


def load_registry(path: str | Path = REPO_ROOT / "configs" / "experiments" / "registry.yaml") -> Registry:
    """Load and validate every spec in the registry file."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    reg = Registry()
    for raw in data["experiments"]:
        reg.register(ExperimentSpec(**raw))
    return reg
