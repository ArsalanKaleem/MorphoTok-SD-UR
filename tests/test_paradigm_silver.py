"""Silver supervision derivation and paradigm-coherence metric (hand-computed values)."""

from __future__ import annotations

import pytest

from morphtok.analyzers.lemma_derived import (
    LemmaDerivedAnalyzer,
    LemmaPair,
    build_silver,
    derive_boundaries,
    group_by_lemma,
    lemma_split,
)
from morphtok.eval.paradigm import common_prefix, paradigm_coherence

ZWNJ = "‌"


def test_derive_boundaries_rules() -> None:
    assert derive_boundaries("abcta", "abcna") == (3,)
    assert derive_boundaries("abc", "abc") == ()
    assert derive_boundaries("xyz", "abc") is None  # suppletion: not derivable
    assert derive_boundaries("abx", "aby", min_stem=3) is None
    assert derive_boundaries("ab cd", "ab") is None  # multiword form
    assert derive_boundaries(f"ab{ZWNJ}cta", "abcna") == (3,)  # stripped coordinates
    assert derive_boundaries("abcna", "abcna") == ()


def test_lemma_split_is_deterministic_and_covers_all() -> None:
    splits = {lemma_split(f"l{i}", "s") for i in range(200)}
    assert splits == {"train", "dev", "test"}
    assert lemma_split("l1", "s") == lemma_split("l1", "s")


def test_build_silver_aggregates_and_never_leaks() -> None:
    pairs = [
        LemmaPair("abcta", "abcna", "VERB", "t"),
        LemmaPair("abcta", "abcna", "VERB", "t"),
        LemmaPair("abcta", "abcxx", "VERB", "t"),  # different lemma, same derived boundary
        LemmaPair("qq", "zz", "NOUN", "t"),
    ]
    entries, stats = build_silver(pairs, salt="s")
    assert stats["not_derivable"] == 1 and stats["types"] == 1
    e = entries["abcta"]
    assert e.majority == (3,) and e.agreement == 1.0
    assert e.lemmas == {"abcna", "abcxx"}
    rank = {"train": 0, "dev": 1, "test": 2}
    assert rank[e.split] == max(rank[lemma_split(lem, "s")] for lem in e.lemmas)


def test_ambiguity_kept_as_weighted_alternatives() -> None:
    pairs = [LemmaPair("abcde", "abcxx", "N", "t")] * 3 + [LemmaPair("abcde", "abxxx", "N", "t")]
    entries, stats = build_silver(pairs, salt="s")
    e = entries["abcde"]
    assert dict(e.variants) == {(3,): 3, (2,): 1}
    assert stats["ambiguous_types"] == 1
    for split in ("train", "dev", "test"):
        e.split = split
        an = LemmaDerivedAnalyzer(entries, use_splits=frozenset({split}), base_confidence=0.8)
        res = {a.boundaries: a.confidence for a in an.analyze("abcde")}
        assert res == {(2,): pytest.approx(0.2), (3,): pytest.approx(0.6)}
    held_out = LemmaDerivedAnalyzer(entries, use_splits=frozenset({"nonexistent"}))
    assert held_out.analyze("abcde") == []


def test_group_by_lemma_skips_multiword() -> None:
    g = group_by_lemma([LemmaPair("ab", "L", "V", "t"), LemmaPair("ab cd", "L", "V", "t")])
    assert g == {"L": {"ab"}}


def test_common_prefix() -> None:
    assert common_prefix(["abcx", "abcy", "abc"]) == "abc"
    assert common_prefix([]) == ""


def test_paradigm_coherence_hand_values() -> None:
    paradigms = {"L1": {"abc", "abcx", "abcyz"}, "L2": {"pqa", "pqb"}, "L3": {"zz"}, "L4": {"ma", "nb"}}

    def coherent(w: str) -> list[str]:
        table = {
            "abc": ["abc"],
            "abcx": ["abc", "x"],
            "abcyz": ["abc", "yz"],
            "pqa": ["pq", "a"],
            "pqb": ["pqb"],
        }
        return table[w]

    r = paradigm_coherence(paradigms, coherent)
    # L3 has 1 form, L4 has empty stem -> excluded; L1 coherent; L2: "pqb" not split at 2
    assert r["n_paradigms"] == 2
    assert r["coherence"] == pytest.approx(0.5)
    # forms longer than stem: abcx, abcyz, pqa, pqb -> 3 of 4 stem-aligned
    assert r["stem_boundary_rate"] == pytest.approx(3 / 4)
    assert r["mean_stem_variants"] == pytest.approx((1 + 2) / 2)


def test_paradigm_coherence_rejects_bad_tokenizer() -> None:
    with pytest.raises(ValueError):
        paradigm_coherence({"L": {"ab", "abc"}}, lambda w: ["x"])


def test_merge_silver_keeps_variants_and_most_restrictive_split() -> None:
    from collections import Counter

    from morphtok.analyzers.lemma_derived import SilverEntry, merge_silver

    a = {"w": SilverEntry("w", Counter({(2,): 1}), set(), "train", {"A"})}
    b = {
        "w": SilverEntry("w", Counter({(3,): 1}), set(), "dev", {"B"}),
        "v": SilverEntry("v", Counter({(): 1}), set(), "train", {"B"}),
    }
    m = merge_silver([a, b])
    assert dict(m["w"].variants) == {(2,): 1, (3,): 1}
    assert m["w"].split == "dev" and m["w"].sources == {"A", "B"}
    assert a["w"].split == "train"  # inputs not mutated
    assert set(m) == {"w", "v"}
