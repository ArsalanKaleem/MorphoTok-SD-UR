"""Normalization policies, index maps and the format-character audit."""

from __future__ import annotations

import warnings

import pytest

from morphtok.data.normalize import (
    NormalizationPolicy,
    SelectiveRule,
    ZwnjPolicy,
    process_word,
    strip_format,
    tokens_to_stripped_boundaries,
    unicode_normalize,
)
from morphtok.unicode_audit.contexts import (
    extract_occurrences,
    morph_rate,
    oracle_labels_from_gold,
    stratified_sample,
)
from morphtok.unicode_audit.zwnj_stats import UNAVAILABLE, audit_lines, load_joining_types

ZWNJ = "‌"
ZWJ = "‍"


def test_strip_format_map() -> None:
    s, m = strip_format(f"ab{ZWNJ}c{ZWJ}d")
    assert s == "abcd"
    assert m == [0, 1, 2, 2, 3, 3, 4]


def test_policies() -> None:
    raw = f"ab{ZWNJ}cd"
    keep = process_word(raw, NormalizationPolicy(zwnj=ZwnjPolicy.PRESERVE))
    assert keep.pieces == (raw,)
    rem = process_word(raw, NormalizationPolicy(zwnj=ZwnjPolicy.REMOVE))
    assert rem.pieces == ("abcd",) and rem.to_stripped == (0, 1, 2, 3, 4)
    mark = process_word(raw, NormalizationPolicy(zwnj=ZwnjPolicy.BOUNDARY_MARKER))
    assert mark.pieces == ("ab", "cd") and mark.forced_boundaries == (2,)


def test_marker_at_word_edge_is_not_a_split() -> None:
    pw = process_word(f"{ZWNJ}ab{ZWNJ}", NormalizationPolicy(zwnj=ZwnjPolicy.BOUNDARY_MARKER))
    assert pw.pieces == ("ab",)


def test_zwj_is_not_touched_by_zwnj_policy() -> None:
    pw = process_word(f"a{ZWJ}b", NormalizationPolicy(zwnj=ZwnjPolicy.REMOVE))
    assert pw.processed == f"a{ZWJ}b"


def test_selective_without_rules_warns_and_preserves() -> None:
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        pw = process_word(f"a{ZWNJ}b", NormalizationPolicy(zwnj=ZwnjPolicy.SELECTIVE))
    assert pw.processed == f"a{ZWNJ}b"
    assert any("no approved rules" in str(x.message) for x in w)


def test_selective_with_rule() -> None:
    rule = SelectiveRule(frozenset("a"), frozenset("b"), "remove", approved_by="unit-test")
    pol = NormalizationPolicy(zwnj=ZwnjPolicy.SELECTIVE, selective_rules=[rule])
    assert process_word(f"a{ZWNJ}b", pol).processed == "ab"
    assert process_word(f"c{ZWNJ}b", pol).processed == f"c{ZWNJ}b"


def test_stripped_boundaries_collapse_around_zwnj() -> None:
    pw = process_word(f"ab{ZWNJ}cd", NormalizationPolicy())
    assert tokens_to_stripped_boundaries(pw, ["ab", ZWNJ, "cd"]) == {2}
    assert tokens_to_stripped_boundaries(pw, [f"ab{ZWNJ}", "cd"]) == {2}
    assert tokens_to_stripped_boundaries(pw, ["a", f"b{ZWNJ}c", "d"]) == {1, 3}


def test_unicode_normalize_forms() -> None:
    decomposed = "é"
    assert unicode_normalize(decomposed, "NFC") == "é"
    assert unicode_normalize(decomposed, "none") == decomposed
    with pytest.raises(ValueError):
        unicode_normalize("x", "NFX")


def test_audit_counts_and_positions() -> None:
    lines = [f"ab{ZWNJ}c d{ZWNJ}{ZWNJ}e", f"{ZWJ}x"]
    a = audit_lines(lines)
    z = a["format_chars"]["U+200C"]
    assert z["count"] == 3
    assert z["words_containing"] == 2
    assert z["run_lengths"] == {"1": 1, "2": 1}
    assert z["position"] == {"medial": 2}
    assert a["format_chars"]["U+200D"]["position"] == {"initial": 1}
    assert a["joining_data"] == UNAVAILABLE
    assert a["format_chars"]["U+200C"]["left_joining"] == {UNAVAILABLE: 2}


def test_joining_table_parse(tmp_path) -> None:  # type: ignore[no-untyped-def]
    f = tmp_path / "ArabicShaping.txt"
    f.write_text("# comment\n0061; LATIN A TEST; D; NO_JOINING_GROUP\n", encoding="utf-8")
    t = load_joining_types(f)
    assert t == {0x61: "D"}
    a = audit_lines([f"a{ZWNJ}b"], joining_table=t)
    assert a["format_chars"]["U+200C"]["left_joining"] == {"D": 1}
    assert load_joining_types(tmp_path / "missing.txt") is None


def test_occurrences_and_oracle_labels() -> None:
    occs = extract_occurrences([f"ab{ZWNJ}cd e{ZWNJ}fg"])
    assert [o.stripped_position for o in occs] == [2, 1]
    labels = oracle_labels_from_gold(occs, {"abcd": (2,), "efg": (2,)})
    assert sorted(labels.values()) == ["MORPH", "ORTHO"]
    r = morph_rate(labels)
    assert r["morph_rate"] == 0.5 and r["denominator"] == 2
    assert len(stratified_sample(occs, 1, seed=0)) >= 1


def test_foreign_and_error_excluded_from_morph_rate() -> None:
    r = morph_rate({"a": "MORPH", "b": "ORTHO", "c": "FOREIGN", "d": "ERROR", "e": "AMBIG"})
    assert r["denominator"] == 3
    assert r["morph_rate"] == pytest.approx(1 / 3)


def test_annotation_sheet_with_bom_and_dropped_trailing_cells(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from morphtok.unicode_audit.contexts import load_annotations

    p = tmp_path / "sheet.tsv"
    p.write_text(
        "occ_id\tstratum\tword\tlabel\tannotator\tnote\nL1\ts\tw\tforeign\nL2\ts\tw\n", encoding="utf-8-sig"
    )
    assert load_annotations(p) == {"L1": [("A1", "FOREIGN")]}
