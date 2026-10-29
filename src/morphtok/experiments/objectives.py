"""Objective registry and novelty screening (Parts IV and XI).

Objectives are recorded in ``configs/experiments/objectives.yaml``; the derivations
are in ``docs/objectives.md``. This module validates that every objective records
the fields required by the master prompt and enforces the novelty-screening gate:
an objective may be labelled ``contribution`` only when its screen is complete and
no equivalence to an existing method was found.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from morphtok.provenance import REPO_ROOT

OBJECTIVE_FIELDS: tuple[str, ...] = (
    "name",
    "definition",
    "motivation",
    "assumptions",
    "relationship_to_established",
    "optimization",
    "complexity",
    "hyperparameters",
    "failure_modes",
    "baselines",
    "falsification_experiment",
    "evidence_for_contribution",
)

SCREEN_STEPS: tuple[str, ...] = (
    "closest_existing_formulation",
    "term_by_term_comparison",
    "equivalence_to_known_method",
    "terminology_search",
    "smallest_new_element",
    "isolating_baseline",
    "disproving_result",
)


@dataclass
class NoveltyScreen:
    """The seven-step screen; every step starts as ``None`` (not done)."""

    closest_existing_formulation: str | None = None
    term_by_term_comparison: str | None = None
    equivalence_to_known_method: bool | None = None
    terminology_search: str | None = None
    smallest_new_element: str | None = None
    isolating_baseline: str | None = None
    disproving_result: str | None = None
    sources_verified: list[str] = field(default_factory=list)

    def incomplete_steps(self) -> list[str]:
        """Steps not yet completed."""
        return [s for s in SCREEN_STEPS if getattr(self, s) in (None, "")]

    def may_claim_novelty(self) -> bool:
        """True only if every step is done, no equivalence was found, and sources were verified."""
        return (
            not self.incomplete_steps()
            and self.equivalence_to_known_method is False
            and bool(self.sources_verified)
        )


@dataclass
class ObjectiveSpec:
    """One candidate objective."""

    objective_id: str
    status: str
    fields: dict[str, object]
    screen: NoveltyScreen

    def validate(self) -> None:
        """Every documented field present; 'contribution' status requires a passed screen."""
        missing = [f for f in OBJECTIVE_FIELDS if f not in self.fields]
        if missing:
            raise ValueError(f"objective {self.objective_id}: missing {missing}")
        if self.status == "contribution" and not self.screen.may_claim_novelty():
            raise ValueError(
                f"objective {self.objective_id} labelled 'contribution' but novelty screen "
                f"incomplete: {self.screen.incomplete_steps()}"
            )


def load_objectives(
    path: str | Path = REPO_ROOT / "configs" / "experiments" / "objectives.yaml",
) -> dict[str, ObjectiveSpec]:
    """Load and validate the objective registry."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    out: dict[str, ObjectiveSpec] = {}
    for raw in data["objectives"]:
        screen = NoveltyScreen(**(raw.pop("novelty_screen", None) or {}))
        spec = ObjectiveSpec(
            objective_id=raw.pop("objective_id"), status=raw.pop("status"), fields=raw, screen=screen
        )
        spec.validate()
        out[spec.objective_id] = spec
    return out
