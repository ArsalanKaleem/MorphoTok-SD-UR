"""Hand-computed expected values for every metric and statistic."""

from __future__ import annotations

import math

import pytest
from audit.agreement import adjudicate, cohen_kappa, fleiss_kappa

from morphtok.downstream.lm_small import BigramLM
from morphtok.downstream.ner import NERTask
from morphtok.eval.exact_match import exact_match
from morphtok.eval.fertility import UnitCounts, fertility, tokens_per_char, vocab_mismatches
from morphtok.eval.morph_boundary import BoundaryCounts, boundary_prf, f1_of_counts, prf
from morphtok.eval.rare_words import frequency_bin, frequency_key, stratified_boundary_metrics
from morphtok.eval.stats import (
    aggregate_seeds,
    approximate_randomization,
    cohens_dz,
    paired_bootstrap,
    percentile,
    t_critical_975,
    wilson_interval,
)


def test_fertility_ratio_of_sums() -> None:
    units = [UnitCounts(5, 2, 10), UnitCounts(1, 2, 6)]
    assert fertility(units) == pytest.approx(6 / 4)
    assert tokens_per_char(units) == pytest.approx(6 / 16)
    assert fertility([]) is None
    assert tokens_per_char([UnitCounts(0, 0, 0)]) is None


def test_vocab_mismatch() -> None:
    assert vocab_mismatches({"a": 100, "b": 98}, 100) == {"b": 98}
    assert vocab_mismatches({"a": 100, "b": 98}, 100, tolerance=2) == {}


def test_boundary_prf_hand() -> None:
    preds = [{1, 3}, {2}, set()]
    golds = [{1}, {2, 4}, {1}]
    r = boundary_prf(preds, golds)
    # TP = 1 + 1 + 0 = 2; n_pred = 3; n_gold = 4
    assert r["precision"] == pytest.approx(2 / 3)
    assert r["recall"] == pytest.approx(2 / 4)
    assert r["f1"] == pytest.approx(2 * (2 / 3) * 0.5 / (2 / 3 + 0.5))


def test_boundary_prf_undefined_cases() -> None:
    assert boundary_prf([set()], [{1}])["precision"] is None
    assert boundary_prf([set()], [{1}])["f1"] is None
    assert boundary_prf([{1}], [set()])["recall"] is None
    assert prf(BoundaryCounts(0, 2, 2))["f1"] == 0.0
    assert f1_of_counts([BoundaryCounts(0, 0, 1)]) == 0.0
    with pytest.raises(ValueError):
        boundary_prf([set()], [])


def test_exact_match() -> None:
    assert exact_match([{1}, {2}, set()], [{1}, {3}, set()]) == pytest.approx(2 / 3)
    assert exact_match([], []) is None


def test_frequency_bins() -> None:
    edges = [0, 1, 5]
    assert frequency_bin(0, edges) == "0"
    assert frequency_bin(1, edges) == "1"
    assert frequency_bin(3, edges) == "2-5"
    assert frequency_bin(5, edges) == "2-5"
    assert frequency_bin(6, edges) == ">5"


def test_stratified_metrics() -> None:
    key = frequency_key({"seen": 3}, [0, 5])
    out = stratified_boundary_metrics(["seen", "new"], [{1}, {1}], [{1}, {2}], key)
    assert out["0"]["f1"] == 0.0 and out["0"]["n_words"] == 1
    assert out["1-5"]["f1"] == 1.0


def test_percentile_and_t() -> None:
    assert percentile([1.0, 2.0, 3.0, 4.0], 0.5) == pytest.approx(2.5)
    assert t_critical_975(1) == 12.706
    assert t_critical_975(100) == t_critical_975(30)
    with pytest.raises(ValueError):
        t_critical_975(0)


def test_aggregate_seeds_counts_failures() -> None:
    agg = aggregate_seeds([1.0, 2.0, 3.0, None])
    assert agg["n_failed"] == 1 and agg["n_ok"] == 3
    assert agg["mean"] == pytest.approx(2.0)
    assert agg["sd"] == pytest.approx(1.0)
    half = 4.303 * 1.0 / math.sqrt(3)
    assert agg["ci_low"] == pytest.approx(2.0 - half)
    assert aggregate_seeds([None])["mean"] is None
    assert aggregate_seeds([5.0])["sd"] is None


def test_cohens_dz() -> None:
    assert cohens_dz([1.0, 2.0, 3.0]) == pytest.approx(2.0)
    assert cohens_dz([1.0]) is None
    assert cohens_dz([1.0, 1.0]) is None


def test_wilson() -> None:
    lo, hi = wilson_interval(5, 10)  # type: ignore[misc]
    assert lo == pytest.approx(0.2366, abs=1e-3) and hi == pytest.approx(0.7634, abs=1e-3)
    assert wilson_interval(0, 0) is None


def mean(xs) -> float:  # type: ignore[no-untyped-def]
    return sum(xs) / len(xs)


def test_paired_bootstrap_identical_systems_zero() -> None:
    a = [1.0, 2.0, 3.0, 4.0]
    r = paired_bootstrap(a, a, mean, n_boot=200, seed=0)
    assert r["delta"] == 0.0 and r["ci_low"] == 0.0 and r["ci_high"] == 0.0


def test_paired_bootstrap_constant_shift() -> None:
    a = [1.0, 2.0, 3.0, 4.0]
    b = [x + 1 for x in a]
    r = paired_bootstrap(a, b, mean, n_boot=200, seed=0)
    assert r["delta"] == pytest.approx(1.0)
    assert r["ci_low"] == pytest.approx(1.0) and r["ci_high"] == pytest.approx(1.0)
    assert r["p_two_sided"] == 0.0


def test_approximate_randomization() -> None:
    a = [0.0] * 30
    b = [1.0] * 30
    assert approximate_randomization(a, b, mean, n_perm=200, seed=0)["p_value"] < 0.01
    same = approximate_randomization(a, a, mean, n_perm=50, seed=0)
    assert same["p_value"] == 1.0


def test_kappa_hand() -> None:
    a = ["M", "M", "O", "O"]
    b = ["M", "O", "O", "O"]
    # po = 3/4; pe = (2*1 + 2*3)/16 = 0.5 ; kappa = 0.5
    assert cohen_kappa(a, b) == pytest.approx(0.5)
    assert cohen_kappa(["M"], ["M"]) is None
    assert fleiss_kappa([["M", "M"], ["O", "O"]]) == pytest.approx(1.0)
    adj = adjudicate({"x": [("p", "M"), ("q", "O")], "y": [("p", "M"), ("q", "M"), ("r", "O")]})
    assert adj == {"x": "AMBIG", "y": "M"}


def test_bigram_bits_per_char() -> None:
    lm = BigramLM(k=1.0)
    lm.fit([["a", "b"]])
    # vocab = {<s>, a, b, </s>, <unk>} = 5; p(a|<s>) = 2/6, p(b|a) = 2/6, p(</s>|b) = 2/6
    expected = -3 * math.log2(2 / 6) / 2
    assert lm.bits_per_char([["a", "b"]], 2) == pytest.approx(expected)
    assert lm.bits_per_char([["a"]], 0) is None


def test_ner_alignment() -> None:
    t = NERTask()
    assert t.align_labels(["B-PER", "O"], [2, 1]) == ["B-PER", "IGNORE", "O"]
    t2 = NERTask(label_alignment="all_subwords")
    assert t2.align_labels(["B-PER"], [3]) == ["B-PER", "I-PER", "I-PER"]
