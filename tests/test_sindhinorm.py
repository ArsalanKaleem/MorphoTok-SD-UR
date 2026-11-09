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
    assert sindhinorm.normalize("ھن") == "هن"  # do-chashmi heh, majority spelling
    assert sindhinorm.normalize("ڪي کي") == "ڪي کي"  # two different words


def test_explain_rules() -> None:
    rules = {r["word"]: r["rule"] for r in sindhinorm.explain("کی ھن ڪتاب کري آهی")}
    assert rules == {"کی": "native-keep", "ھن": "encoding-merge", "ڪتاب": "already-canonical",
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
