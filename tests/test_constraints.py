"""Constraint semantics, edge-cost decomposition and analyzer-to-constraint mapping."""

from __future__ import annotations

import itertools

import pytest

from morphtok.analyzers.base import Analysis, NullAnalyzer, coverage
from morphtok.analyzers.confidence import (
    SupervisionConfig,
    aggregate,
    calibration_table,
    constraints_for_word,
)
from morphtok.analyzers.rules_sindhi import SindhiRuleAnalyzer, load_rules
from morphtok.data.normalize import NormalizationPolicy, ZwnjPolicy, process_word
from morphtok.tokenizers.constraints import (
    BoundaryConstraint,
    BoundaryType,
    WordConstraints,
    boundaries_of,
    penalty_log_odds,
    penalty_threshold,
    validate_segmentation,
)

ZWNJ = "‌"


def all_boundary_sets(n: int) -> list[set[int]]:
    pos = list(range(1, n))
    return [set(c) for r in range(len(pos) + 1) for c in itertools.combinations(pos, r)]


def segmentation_edges(n: int, bounds: set[int]) -> list[tuple[int, int]]:
    pts = [0, *sorted(bounds), n]
    return list(itertools.pairwise(pts))


def test_unknown_is_default_and_free() -> None:
    wc = WordConstraints.empty(5)
    assert wc.kind_at(2) is BoundaryType.UNKNOWN
    assert wc.violation_cost({1, 3}) == 0.0
    assert wc.is_hard_feasible({1, 2, 3, 4})


def test_edge_costs_sum_to_violation_cost() -> None:
    wc = WordConstraints.from_iterable(
        6,
        [
            BoundaryConstraint(1, BoundaryType.MANDATORY, 0.9),
            BoundaryConstraint(3, BoundaryType.PREFERRED, 0.4),
            BoundaryConstraint(4, BoundaryType.FORBIDDEN, 0.7),
        ],
    )
    for b in all_boundary_sets(6):
        total = sum(wc.edge_cost(i, j) for i, j in segmentation_edges(6, b))
        assert total == pytest.approx(wc.violation_cost(b))


def test_hard_edges_match_feasibility() -> None:
    wc = WordConstraints.from_iterable(
        5,
        [
            BoundaryConstraint(2, BoundaryType.MANDATORY, 0.5),
            BoundaryConstraint(3, BoundaryType.FORBIDDEN, 0.5),
            BoundaryConstraint(1, BoundaryType.PREFERRED, 0.5),
        ],
    )
    for b in all_boundary_sets(5):
        edges_ok = all(wc.edge_allowed_hard(i, j) for i, j in segmentation_edges(5, b))
        assert edges_ok == wc.is_hard_feasible(b)


def test_preferred_is_never_a_hard_exclusion() -> None:
    wc = WordConstraints.from_iterable(3, [BoundaryConstraint(1, BoundaryType.PREFERRED, 1.0)])
    assert wc.is_hard_feasible(set())
    assert wc.violation_cost(set()) == 1.0


def test_invalid_positions_and_confidence() -> None:
    with pytest.raises(ValueError):
        WordConstraints.from_iterable(3, [BoundaryConstraint(3, BoundaryType.MANDATORY, 0.5)])
    with pytest.raises(ValueError):
        BoundaryConstraint(1, BoundaryType.MANDATORY, 1.5)
    with pytest.raises(ValueError):
        WordConstraints(3, {}, penalty="nope")


def test_penalty_mappings() -> None:
    assert penalty_log_odds(0.5) == pytest.approx(0.0)
    assert penalty_log_odds(0.2) == 0.0
    assert penalty_log_odds(1.0) < 20  # clipped, finite
    assert penalty_threshold(0.49) == 0.0
    assert penalty_threshold(0.5) == 1.0


def test_boundaries_and_validation() -> None:
    assert boundaries_of(["ab", "c", "de"]) == [2, 3]
    assert boundaries_of(["abc"]) == []
    validate_segmentation("abc", ["a", "bc"])
    with pytest.raises(ValueError):
        validate_segmentation("abc", ["a", "b"])
    with pytest.raises(ValueError):
        validate_segmentation("abc", ["a", "", "bc"])


def test_aggregate_ambiguous_analyses() -> None:
    a1 = Analysis((2,), 0.8, "t", "1")
    a2 = Analysis((2, 4), 0.2, "t", "1")
    agg = aggregate([a1, a2])
    # r = 0.8; support(2) = 1.0, support(4) = 0.2
    assert agg[2] == pytest.approx(0.8)
    assert agg[4] == pytest.approx(0.8 * 0.2)
    assert aggregate([]) == {}


def test_constraints_map_through_zwnj_preserve_and_marker() -> None:
    raw = f"ab{ZWNJ}cd"
    ana = [Analysis((2,), 0.9, "t", "1")]
    cfg = SupervisionConfig()
    pw = process_word(raw, NormalizationPolicy(zwnj=ZwnjPolicy.PRESERVE))
    (wc,) = constraints_for_word(pw, ana, cfg)
    assert wc is not None
    # format char attaches left: boundary after the ZWNJ (processed position 3)
    assert set(wc.constraints) == {3}
    pw_r = process_word(raw, NormalizationPolicy(zwnj=ZwnjPolicy.REMOVE))
    (wc_r,) = constraints_for_word(pw_r, ana, cfg)
    assert wc_r is not None and set(wc_r.constraints) == {2}
    pw_m = process_word(raw, NormalizationPolicy(zwnj=ZwnjPolicy.BOUNDARY_MARKER))
    assert pw_m.pieces == ("ab", "cd")
    assert constraints_for_word(pw_m, ana, cfg) == [None, None]  # boundary is already forced


def test_absence_of_analysis_is_unknown_not_forbidden() -> None:
    pw = process_word("abcd", NormalizationPolicy())
    (wc,) = constraints_for_word(pw, [Analysis((2,), 0.9, "t", "1")], SupervisionConfig())
    assert wc is not None
    assert wc.kind_at(1) is BoundaryType.UNKNOWN and wc.kind_at(3) is BoundaryType.UNKNOWN
    forb = SupervisionConfig(covered_absent="forbidden", covered_absent_confidence=0.3)
    (wc2,) = constraints_for_word(pw, [Analysis((2,), 0.9, "t", "1")], forb)
    assert wc2 is not None and wc2.kind_at(1) is BoundaryType.FORBIDDEN
    assert constraints_for_word(pw, [], SupervisionConfig()) == [None]


def test_null_analyzer_and_coverage() -> None:
    rep = coverage(NullAnalyzer(), [("ab", 3), ("cd", 1)])
    assert rep.configured is False
    assert rep.type_coverage == 0.0 and rep.token_coverage == 0.0
    assert rep.n_types == 2 and rep.n_tokens == 4


def test_sindhi_rules_require_provenance(tmp_path) -> None:  # type: ignore[no-untyped-def]
    assert SindhiRuleAnalyzer(None).is_configured is False
    bad = tmp_path / "bad.yaml"
    bad.write_text("rules:\n  - {kind: suffix, affix: xy, confidence: 0.5}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_rules(bad)
    good = tmp_path / "good.yaml"
    good.write_text(
        "version: test\nrules:\n  - {kind: suffix, affix: xy, confidence: 0.5, source: unit-test}\n",
        encoding="utf-8",
    )
    an = SindhiRuleAnalyzer(good)
    assert an.is_configured
    assert an.analyze("abcxy")[0].boundaries == (3,)
    assert an.analyze("xy") == []  # stem too short


def test_calibration_table_hand_values() -> None:
    pred = {"w": {1: 0.95, 2: 0.95, 3: 0.15}}
    gold = {"w": [1, 3]}
    cal = calibration_table(pred, gold, n_bins=10)
    assert cal["n"] == 3
    # bin 9: conf .95 x2, acc .5 -> |.5-.95| * 2/3 ; bin 1: conf .15, acc 1 -> |1-.15| * 1/3
    assert cal["ece"] == pytest.approx((2 / 3) * 0.45 + (1 / 3) * 0.85)
