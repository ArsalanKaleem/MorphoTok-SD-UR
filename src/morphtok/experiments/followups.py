"""Evidence-driven follow-up hypothesis generation (Part XI).

:func:`propose_followups` inspects a *measured* comparison summary and emits
conditional follow-up hypotheses. Each is saved with status ``proposed`` and
literature status ``unverified``; nothing is ever promoted to a claim automatically.
Schema: ``schemas/hypothesis.schema.json``.

The trigger rules encode the conditional research directions of the master prompt;
they fire only on measured patterns, and on synthetic data the records carry
``synthetic: true``.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from morphtok.provenance import now_utc


@dataclass
class FollowUp:
    """One follow-up hypothesis record."""

    hypothesis_id: str
    parent_experiment_id: str
    observed_evidence: str
    alternative_explanations: list[str]
    proposed_intervention: str
    expected_outcomes: dict[str, str]
    minimum_discriminating_experiment: str
    confounds: list[str]
    computational_cost: str
    literature_verification_status: str = "unverified"
    decision_criteria: str = ""
    result: str | None = None
    followup_decision: str | None = None
    status: str = "proposed"
    synthetic: bool = False
    created: str = field(default_factory=now_utc)


def _ci_excludes_zero(d: dict[str, float] | None) -> bool:
    return bool(d) and (d["ci_low"] > 0 or d["ci_high"] < 0)  # type: ignore[index]


def propose_followups(parent_id: str, summary: dict[str, Any], synthetic: bool) -> list[FollowUp]:
    """Rule-based proposals from a comparison summary.

    Expected ``summary`` keys (all optional): ``fertility_delta``, ``f1_delta`` (paired
    bootstrap dicts, B - A), ``normalization_share`` (float), ``soft_minus_hard_f1``
    (bootstrap dict), ``seed_sd_f1`` (float), ``f1_delta_covered`` /
    ``f1_delta_uncovered`` (bootstrap dicts), ``perturbation_slope`` (float, F1 change
    per unit analyzer noise).
    """
    out: list[FollowUp] = []
    n = 0

    def add(**kw: Any) -> None:
        nonlocal n
        n += 1
        out.append(FollowUp(hypothesis_id=f"{parent_id}-FU{n:02d}", parent_experiment_id=parent_id,
                            synthetic=synthetic, **kw))  # fmt: skip

    fd, f1d = summary.get("fertility_delta"), summary.get("f1_delta")
    if fd and f1d and fd["delta"] < 0 and _ci_excludes_zero(fd) and not _ci_excludes_zero(f1d):
        add(
            observed_evidence=f"fertility changed by {fd['delta']:.4f} (CI excludes 0) while "
            f"boundary-F1 delta {f1d['delta']:.4f} has a CI including 0",
            alternative_explanations=["longer tokens", "memorised frequent words", "format-char deletion"],
            proposed_intervention="stratify by token length and training frequency; recompute F1 on unseen types",
            expected_outcomes={
                "longer tokens": "mean token length rises; F1 unchanged in all strata",
                "memorised frequent words": "fertility gain concentrated in high-frequency bin",
                "format-char deletion": "gain disappears when comparing within the same ZWNJ policy",
            },
            minimum_discriminating_experiment="frequency x length stratified re-analysis of existing runs (no retraining)",
            confounds=["vocabulary size", "normalization policy"],
            computational_cost="negligible (re-analysis)",
            decision_criteria="drop efficiency-based claims if gain is explained by one stratum",
        )
    share = summary.get("normalization_share")
    if share is not None and share >= 0.5:
        add(
            observed_evidence=f"normalization explains {share:.2f} of the fertility difference",
            alternative_explanations=["ZWNJ handling is the effect", "residual morphological effect is real"],
            proposed_intervention="compare morphology-aware variants only within the ZWNJ-removed policy",
            expected_outcomes={
                "ZWNJ handling is the effect": "no residual difference within the removed policy",
                "residual morphological effect is real": "residual F1 gain with CI excluding 0",
            },
            minimum_discriminating_experiment="unigram_soft vs unigram on the remove policy, matched vocab, 3 seeds",
            confounds=["analyzer coverage"],
            computational_cost="3 seeds x 2 systems x |vocab sizes| trainings",
            decision_criteria="remove the ZWNJ-loss claim (Gate 0) if residual CI includes 0",
        )
    sh = summary.get("soft_minus_hard_f1")
    if sh and sh["ci_high"] <= 0:
        add(
            observed_evidence=f"soft minus hard F1 = {sh['delta']:.4f}, CI upper bound <= 0",
            alternative_explanations=["analyzer is precise enough for hard use", "lambda too small"],
            proposed_intervention="lambda sweep to the hard limit; compare at the best dev lambda",
            expected_outcomes={
                "analyzer is precise enough for hard use": "soft approaches hard from below as lambda grows",
                "lambda too small": "some finite lambda exceeds hard on dev",
            },
            minimum_discriminating_experiment="Family B lambda sensitivity on dev only",
            confounds=["dev/test leakage if lambda chosen on test"],
            computational_cost="|lambda grid| x 3 seeds trainings",
            decision_criteria="prefer hard constraints (simpler) unless soft wins on dev and test",
        )
    sd = summary.get("seed_sd_f1")
    if sd is not None and f1d and abs(f1d["delta"]) < 2 * sd:
        add(
            observed_evidence=f"between-seed sd {sd:.4f} comparable to effect {f1d['delta']:.4f}",
            alternative_explanations=["effect is seed noise", "effect is real but small"],
            proposed_intervention="increase seeds and training-data size",
            expected_outcomes={
                "effect is seed noise": "mean delta shrinks toward 0 with more seeds",
                "effect is real but small": "CI over seeds tightens around a non-zero value",
            },
            minimum_discriminating_experiment="10 seeds at one vocabulary size",
            confounds=["subsampling fraction"],
            computational_cost="10 trainings per system",
            decision_criteria="report as unresolved if CI over seeds includes 0",
        )
    cov, unc = summary.get("f1_delta_covered"), summary.get("f1_delta_uncovered")
    if cov and unc and _ci_excludes_zero(cov) and not _ci_excludes_zero(unc):
        add(
            observed_evidence="gain present on analyzer-covered words only",
            alternative_explanations=["method copies analyzer output", "vocabulary generalises poorly"],
            proposed_intervention="evaluate with analyzer disabled at decode time (train-only supervision)",
            expected_outcomes={
                "method copies analyzer output": "gain vanishes with decode-time supervision off",
                "vocabulary generalises poorly": "gain on covered words persists without decode supervision",
            },
            minimum_discriminating_experiment="train_mode=soft, decode_mode=none vs soft/soft",
            confounds=["coverage correlates with frequency"],
            computational_cost="re-decode existing models",
            decision_criteria="claim only train-time benefit if decode-time supervision is required",
        )
    slope = summary.get("perturbation_slope")
    if slope is not None and slope < 0:
        add(
            observed_evidence=f"boundary F1 falls with analyzer noise (slope {slope:.4f})",
            alternative_explanations=["confidence is uncalibrated", "supervision should be selective"],
            proposed_intervention="calibrate confidences on dev gold; compare high-confidence-only supervision",
            expected_outcomes={
                "confidence is uncalibrated": "calibrated weights flatten the slope",
                "supervision should be selective": "min_confidence threshold flattens the slope more",
            },
            minimum_discriminating_experiment="Family C perturbation grid x {linear, threshold} penalty",
            confounds=["perturbation type"],
            computational_cost="|noise grid| x 2 trainings",
            decision_criteria="adopt the simpler variant if both flatten equally",
        )
    return out


def save_followups(items: list[FollowUp], path: Path) -> None:
    """Append follow-ups to a JSONL store."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for it in items:
            fh.write(json.dumps(asdict(it), ensure_ascii=False) + "\n")
