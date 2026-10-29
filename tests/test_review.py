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
