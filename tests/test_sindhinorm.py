"""The pip package ``sindhinorm``: bundled lexicon, explain rules, CLI, re-export."""

from __future__ import annotations

import json

import pytest

sindhinorm = pytest.importorskip("sindhinorm")
from sindhinorm.cli import main  # noqa: E402


def test_bundled_lexicon_and_examples() -> None:
    norm = sindhinorm.default_normalizer()
    assert len(norm.lexicon) > 50_000
    assert sindhinorm.normalize("هي ڪتاب آهی") == "هي ڪتاب آهي"  # Farsi yeh
    assert sindhinorm.normalize("ھن") == "ھن"  # both heh shapes are Sindhi: kept by default
    assert sindhinorm.normalize("ڪي کي") == "ڪي کي"  # two different words


def test_explain_rules() -> None:
    rules = {r["word"]: r["rule"] for r in sindhinorm.explain("کی ھن ڪتاب کري آهی")}
    assert rules == {"کی": "native-keep", "ھن": "already-canonical", "ڪتاب": "already-canonical",
                     "کري": "native-keep", "آهی": "encoding-merge"}  # fmt: skip
    assert sindhinorm.explain("123, 45!") == []


def test_reexport_is_same_object() -> None:
    from morphtok.tools import sdnorm

    assert sdnorm.Normalizer is sindhinorm.Normalizer


def test_cli(tmp_path, capsys) -> None:
    src = tmp_path / "in.txt"
    src.write_text("هي ڪتاب آهی\n", encoding="utf-8")
    out = tmp_path / "out.txt"
    assert main([str(src), "-o", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == "هي ڪتاب آهي\n"
    assert main(["explain", "--json", "آهی"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows[0]["output"] == "آهي"
    lex = tmp_path / "lex.json.gz"
    assert main(["build-lexicon", str(src), "-o", str(lex), "--min-count", "1"]) == 0
    norm = sindhinorm.Normalizer.load(lex)
    assert norm.lexicon["ڪتاب"] == 1


def test_keyboard_mode_leaves_standard_sindhi_alone() -> None:
    norm = sindhinorm.default_normalizer()
    # words that 0.1.0 (frequency mode) rewrote towards Wikipedia's majority spelling
    for word in ("عبدالقدير", "شهر", "ڇونه", "دهشتگردي", "لڪيل"):
        assert norm.normalize_word(word) == word
    freq = sindhinorm.Normalizer(norm.lexicon, mode="frequency")
    assert freq.normalize_word("لڪيل") == "لکيل"  # the 0.1.0 behaviour, kept for reproducibility


def test_keyboard_mode_never_writes_keyboard_letters() -> None:
    norm = sindhinorm.default_normalizer()
    bad = sindhinorm.NON_SINDHI
    for word in norm.lexicon:
        out = norm.normalize_word(word)
        if out != word:
            assert not any(c in bad for c in out), (word, out)
            assert all(a == b or a in bad or (a == "ک" and b == "ڪ") for a, b in zip(word, out, strict=True))


def test_keyboard_mode_fixes_keyboard_typing() -> None:
    norm = sindhinorm.default_normalizer()
    assert norm.normalize("ہن ڪتاب آهی، كتاب کتاب") == "هن ڪتاب آهي، ڪتاب ڪتاب"


def test_fold_heh_option() -> None:
    norm = sindhinorm.Normalizer(sindhinorm.default_normalizer().lexicon, fold_heh=True)
    assert norm.normalize_word("ھن") == "هن"
    with pytest.raises(ValueError):
        sindhinorm.Normalizer(norm.lexicon, mode="other")
