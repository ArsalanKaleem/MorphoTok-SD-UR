"""Numerical tests of the reference Unigram lattice against exhaustive enumeration."""

from __future__ import annotations

import math
import random
from collections import Counter

import pytest

from morphtok.tokenizers.constraints import (
    BoundaryType,
    ConstraintMode,
    InfeasibleConstraintsError,
    constraints_from_mapping,
)
from morphtok.tokenizers.lattice_unigram import (
    NoValidSegmentationError,
    UnigramModel,
    UnigramTrainer,
    logsumexp,
)
from morphtok.tokenizers.sampling import sampling_stability

LOGP = {
    "a": math.log(0.2),
    "b": math.log(0.2),
    "c": math.log(0.1),
    "ab": math.log(0.25),
    "bc": math.log(0.15),
    "abc": math.log(0.1),
}


@pytest.fixture
def model() -> UnigramModel:
    return UnigramModel(dict(LOGP), max_piece_len=3)


def test_logsumexp_stable() -> None:
    assert logsumexp([]) == float("-inf")
    assert logsumexp([float("-inf"), float("-inf")]) == float("-inf")
    assert logsumexp([1000.0, 1000.0]) == pytest.approx(1000.0 + math.log(2))
    assert logsumexp([-1000.0, -1000.0]) == pytest.approx(-1000.0 + math.log(2))


def test_partition_matches_enumeration(model: UnigramModel) -> None:
    lat = model.lattice("abc")
    segs = lat.enumerate_all()
    # abc, ab|c, a|bc, a|b|c
    assert sorted(tuple(s) for s, _ in segs) == sorted([("abc",), ("ab", "c"), ("a", "bc"), ("a", "b", "c")])
    z = logsumexp([sc for _, sc in segs])
    assert lat.log_partition() == pytest.approx(z)
    # hand computation
    hand = math.log(0.1 + 0.25 * 0.1 + 0.2 * 0.15 + 0.2 * 0.2 * 0.1)
    assert lat.log_partition() == pytest.approx(hand)


def test_forward_backward_consistent(model: UnigramModel) -> None:
    lat = model.lattice("abcab")
    assert lat.forward()[-1] == pytest.approx(lat.backward()[0])


def test_edge_marginals_sum_to_expected_pieces(model: UnigramModel) -> None:
    lat = model.lattice("abc")
    marg = lat.edge_marginals()
    segs = lat.enumerate_all()
    z = sum(math.exp(sc) for _, sc in segs)
    expected_len = sum(len(s) * math.exp(sc) for s, sc in segs) / z
    assert sum(marg.values()) == pytest.approx(expected_len)
    # probability that position 0 starts some edge is 1
    assert sum(v for (i, _), v in marg.items() if i == 0) == pytest.approx(1.0)


def test_viterbi_is_argmax(model: UnigramModel) -> None:
    lat = model.lattice("abc")
    best, score = lat.viterbi()
    segs = lat.enumerate_all()
    assert score == pytest.approx(max(sc for _, sc in segs))
    assert best == ["abc"]  # 0.1 beats 0.025, 0.03, 0.004


def test_nbest_matches_sorted_enumeration(model: UnigramModel) -> None:
    lat = model.lattice("abc")
    nb = lat.nbest(4)
    ref = sorted(lat.enumerate_all(), key=lambda t: -t[1])
    assert [s for s, _ in nb] == [s for s, _ in ref]


def test_sampling_distribution_normalises(model: UnigramModel) -> None:
    lat = model.lattice("abc")
    segs = lat.enumerate_all()
    z = sum(math.exp(sc) for _, sc in segs)
    probs = {tuple(s): math.exp(sc) / z for s, sc in segs}
    assert sum(probs.values()) == pytest.approx(1.0)
    rng = random.Random(0)
    n = 20000
    c = Counter(tuple(lat.sample(rng)) for _ in range(n))
    assert set(c) <= set(probs)
    for s, p in probs.items():
        assert c[s] / n == pytest.approx(p, abs=0.015)


def test_alpha_flattens_distribution(model: UnigramModel) -> None:
    sharp = model.lattice("abc", alpha=1.0).entropy()
    flat = model.lattice("abc", alpha=0.1).entropy()
    assert flat > sharp
    assert flat <= math.log(4) + 1e-9


def test_entropy_matches_enumeration(model: UnigramModel) -> None:
    lat = model.lattice("abc")
    segs = lat.enumerate_all()
    z = sum(math.exp(sc) for _, sc in segs)
    h = -sum((math.exp(sc) / z) * (sc - math.log(z)) for _, sc in segs)
    assert lat.entropy() == pytest.approx(h)


def test_empty_word(model: UnigramModel) -> None:
    lat = model.lattice("")
    assert lat.log_partition() == 0.0
    assert lat.viterbi() == ([], 0.0)
    assert lat.sample(random.Random(0)) == []
    assert model.encode("") == []


def test_unknown_character_gets_finite_edge(model: UnigramModel) -> None:
    pieces = model.encode("axc")
    assert pieces == ["a", "x", "c"]
    assert math.isfinite(model.lattice("axc").log_partition())


def test_non_finite_logp_rejected() -> None:
    with pytest.raises(ValueError):
        UnigramModel({"a": float("-inf")})
    with pytest.raises(ValueError):
        UnigramModel({"": -1.0})


def test_hard_infeasible_raises_or_falls_back(model: UnigramModel) -> None:
    # FORBIDDEN at 1 and 2 forces the single piece "abc"; MANDATORY at 1 contradicts it.
    wc = constraints_from_mapping(3, {1: (BoundaryType.FORBIDDEN, 1.0), 2: (BoundaryType.FORBIDDEN, 1.0)})
    assert model.encode("abc", wc, mode=ConstraintMode.HARD) == ["abc"]
    bad = constraints_from_mapping(3, {1: (BoundaryType.MANDATORY, 1.0), 2: (BoundaryType.FORBIDDEN, 1.0)})
    # remaining feasible: a|bc  -> feasible. Make it infeasible by removing "bc":
    m2 = UnigramModel({k: v for k, v in LOGP.items() if k != "bc"}, 3)
    with pytest.raises(NoValidSegmentationError):
        m2.lattice("abc", bad, mode=ConstraintMode.HARD).log_partition()
    with pytest.raises(InfeasibleConstraintsError):
        m2.encode("abc", bad, mode=ConstraintMode.HARD, fallback="error")
    assert m2.encode("abc", bad, mode=ConstraintMode.HARD, fallback="unconstrained") == ["abc"]


def test_hard_posterior_restricted_to_feasible_set(model: UnigramModel) -> None:
    wc = constraints_from_mapping(3, {1: (BoundaryType.MANDATORY, 1.0)})
    lat = model.lattice("abc", wc, mode=ConstraintMode.HARD)
    segs = {tuple(s) for s, _ in lat.enumerate_all()}
    assert segs == {("a", "bc"), ("a", "b", "c")}


def test_soft_large_lambda_converges_to_hard(model: UnigramModel) -> None:
    wc = constraints_from_mapping(3, {1: (BoundaryType.MANDATORY, 0.8)})
    hard = model.lattice("abc", wc, mode=ConstraintMode.HARD)
    hz = hard.log_partition()
    hard_p = {tuple(s): math.exp(sc - hz) for s, sc in hard.enumerate_all()}
    soft = model.lattice("abc", wc, lam=200.0, mode=ConstraintMode.SOFT)
    sz = soft.log_partition()
    soft_p = {tuple(s): math.exp(sc - sz) for s, sc in soft.enumerate_all()}
    for s, p in soft_p.items():
        assert p == pytest.approx(hard_p.get(s, 0.0), abs=1e-9)


def test_soft_limit_differs_from_hard_when_infeasible() -> None:
    m = UnigramModel({"a": -1.0, "b": -1.0, "c": -1.0, "abc": -1.0}, 3)
    wc = constraints_from_mapping(3, {1: (BoundaryType.MANDATORY, 1.0), 2: (BoundaryType.FORBIDDEN, 1.0)})
    with pytest.raises(NoValidSegmentationError):
        m.lattice("abc", wc, mode=ConstraintMode.HARD).log_partition()
    # soft still has a distribution: it concentrates on minimum-violation segmentations
    soft = m.lattice("abc", wc, lam=50.0, mode=ConstraintMode.SOFT)
    assert math.isfinite(soft.log_partition())
    best, _ = soft.viterbi()
    assert best in (["abc"], ["a", "b", "c"])  # both violate exactly one constraint


def test_soft_cost_equals_violation(model: UnigramModel) -> None:
    wc = constraints_from_mapping(3, {1: (BoundaryType.MANDATORY, 0.5), 2: (BoundaryType.FORBIDDEN, 0.25)})
    lat = model.lattice("abc", wc, lam=1.0, mode=ConstraintMode.SOFT)
    plain = {tuple(s): sc for s, sc in model.lattice("abc").enumerate_all()}
    for s, sc in lat.enumerate_all():
        from morphtok.tokenizers.constraints import boundaries_of

        v = wc.violation_cost(boundaries_of(s))
        assert sc == pytest.approx(plain[tuple(s)] - v)


def test_sampling_stability_reports(model: UnigramModel) -> None:
    st = sampling_stability(model, "abc", 500, seed=1)
    assert 1 <= st.n_distinct <= 4
    assert 0.0 <= st.viterbi_agreement <= 1.0
    assert st.exact_entropy == pytest.approx(model.lattice("abc").entropy())


def test_trainer_hits_exact_vocab_and_keeps_chars() -> None:
    counts = {"abab": 10, "abc": 5, "cab": 3, "bca": 2}
    tr = UnigramTrainer(vocab_size=8, max_piece_len=4, min_seed_freq=1)
    m = tr.train(counts)
    assert m.vocab_size == 8
    assert {"a", "b", "c"} <= set(m.logp)
    total = sum(math.exp(v) for v in m.logp.values())
    assert total == pytest.approx(1.0)


def test_trainer_rejects_too_small_vocab() -> None:
    with pytest.raises(ValueError):
        UnigramTrainer(vocab_size=2).train({"abc": 1})
