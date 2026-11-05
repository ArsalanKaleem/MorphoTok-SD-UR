"""POS task builder: perturbation mask, matched noise control, CoNLL-U reading."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def bt() -> ModuleType:
    spec = importlib.util.spec_from_file_location("build_pos_tasks", ROOT / "scripts" / "build_pos_tasks.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_perturbation_and_matched_noise(bt: ModuleType) -> None:
    test = [{"id": "s1", "tokens": ["axb", "cd", "xx"], "upos": ["N", "V", "N"], "lemmas": ["a", "c", "x"]}]
    conf, noise = bt.perturb(test, {"x": "y"}, list("abcdxy"), seed=0)
    assert conf[0]["tokens"] == ["ayb", "cd", "yy"]
    assert conf[0]["perturbed"] == [True, False, True] == noise[0]["perturbed"]
    assert noise[0]["tokens"][1] == "cd"  # unperturbed tokens untouched
    for orig, new in zip(test[0]["tokens"], noise[0]["tokens"], strict=True):
        assert len(orig) == len(new)
        assert sum(a != b for a, b in zip(orig, new, strict=True)) == (1 if "x" in orig else 0)
    assert conf[0]["upos"] == test[0]["upos"] and conf[0]["lemmas"] == test[0]["lemmas"]


def test_read_conllu_skips_multiword_and_empty_nodes(bt: ModuleType, tmp_path: Path) -> None:
    p = tmp_path / "x.conllu"
    p.write_text(
        "# sent_id = a\n1-2\tab\t_\t_\t_\t_\t_\t_\t_\t_\n1\ta\tA\tNOUN\t_\t_\t0\troot\t_\t_\n"
        "2\tb\tB\tADP\t_\t_\t1\tcase\t_\t_\n2.1\tc\tC\tX\t_\t_\t_\t_\t_\t_\n\n",
        encoding="utf-8",
    )
    (s,) = bt.read_conllu(p)
    assert s == {"id": "a", "tokens": ["a", "b"], "upos": ["NOUN", "ADP"], "lemmas": ["A", "B"]}
