"""Tests for the native-speaker review importer (scripts/ingest_review.py)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def ir() -> ModuleType:
    spec = importlib.util.spec_from_file_location("ingest_review", ROOT / "scripts" / "ingest_review.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_segmentation_to_boundaries(ir: ModuleType) -> None:
    f = ir.segmentation_to_boundaries
    assert f("abcde", "abc+de") == (3,)
    assert f("abcde", "abc+d+e") == (3, 4)
    assert f("abcde", "abcde") == ()
    assert f("abcde", " abc + de ") == (3,)  # stray spaces tolerated
    assert f("abcde", "abc+dx") is None  # letters changed
    assert f("abcde", "+abcde") is None
    assert f("abcde", "abcde+") is None
    assert f("abcde", "abc++de") is None


def test_ingest_boundaries_uses_only_rows_with_status(
    ir: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    review, gold = tmp_path / "review", tmp_path / "gold"
    review.mkdir()
    gold.mkdir()
    rows = [
        "item_id\tword\tsegmentation\tstatus\tcontext\tnote",
        "x-B001\tabcde\tabc+de\tOK\t\t",
        "x-B002\tfghij\tfghij\tok\t\t",  # reviewed, no boundary
        "x-B003\tklmno\tkl+mno\t?\t\talt: k+lmno",
        "x-B004\tpqrst\tpq+rst\t\t\t",  # edited but no status: not reviewed
        "x-B005\tuvwxy\tSKIP\tSKIP\t\tforeign name",
        "x-B006\tzzzzz\tzz+zzx\tOK\t\t",  # letters changed: rejected
        "x-B007\tabxyz\tab+xyz\tmaybe",  # invalid status, trailing cells dropped
    ]
    (review / "x_boundaries.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8-sig")
    monkeypatch.setattr(ir, "REVIEW", review)
    monkeypatch.setattr(ir, "GOLD", gold)
    ir.ingest_boundaries("x")
    lines = [
        ln
        for ln in (gold / "x_human_dev.tsv").read_text(encoding="utf-8").splitlines()
        if not ln.startswith("#")
    ]
    assert lines == ["abcde\t3\thuman\tdev", "fghij\t\thuman\tdev", "klmno\t2\thuman-unsure\tdev"]
