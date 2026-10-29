"""Synthetic end-to-end integration: fixture determinism, pipelines, registry, records."""

from __future__ import annotations

from collections import Counter

import pytest

from morphtok.analyzers.synthetic import SyntheticOracleAnalyzer
from morphtok.config import load_run_config
from morphtok.data.normalize import strip_format
from morphtok.data.synthetic import SyntheticSpec, generate
from morphtok.experiments.followups import propose_followups
from morphtok.experiments.objectives import NoveltyScreen, load_objectives
from morphtok.experiments.registry import ExperimentSpec, SpecError, load_registry
from morphtok.experiments.results import finalise, new_record, validate_record
from morphtok.experiments.runner import (
    Dataset,
    build_analyzer,
    evaluate,
    load_dataset,
    make_pipeline,
)
from morphtok.provenance import REPO_ROOT
from morphtok.tokenizers.baselines import BPETokenizer, tokenizer_from_dict

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "synthetic"


def test_fixture_is_deterministic_and_1000_lines() -> None:
    corpus = generate()
    text = (FIXTURE / "SYNTHETIC_corpus.txt").read_text(encoding="utf-8")
    assert text.splitlines() == corpus.lines
    assert len(corpus.lines) == 1000


def test_fixture_gold_consistent_with_corpus() -> None:
    corpus = generate()
    for line in corpus.lines[:50]:
        for w in line.split():
            assert strip_format(w)[0] in corpus.gold


def test_fixture_uses_only_artificial_latin_and_format_chars() -> None:
    allowed = set("abcdefghijklmnopqrstuvwxyz ‌‍")
    text = (FIXTURE / "SYNTHETIC_corpus.txt").read_text(encoding="utf-8")
    assert set(text) - {"\n"} <= allowed


@pytest.fixture(scope="module")
def small_ds() -> Dataset:
    run = load_run_config("configs/run/default.yaml")
    return load_dataset(run)


@pytest.fixture(scope="module")
def run_cfg() -> dict:
    return load_run_config("configs/run/default.yaml")


def test_end_to_end_pipelines(small_ds: Dataset, run_cfg: dict) -> None:
    analyzer = build_analyzer(small_ds)
    train = small_ds.splits["train"][:300]
    dev = small_ds.splits["dev"][:60]
    gold = small_ds.gold_for("dev")
    f1 = {}
    for name in ("bpe", "unigram", "unigram_hard", "unigram_soft", "unigram_zwnj_norm"):
        pipe = make_pipeline(run_cfg["tokenizer_cfgs"][name], 120, analyzer)
        pipe.train(train)
        assert pipe.tokenizer.vocab_size == 120
        res = evaluate(pipe, dev, gold)
        assert len(res.line_units) == len(dev)
        assert res.type_words, "dev split must contain gold types"
        # every token sequence reconstructs its pre-tokens
        for line in dev[:10]:
            for pw, toks in pipe.encode_line(line):
                assert "".join(toks) == pw.processed
        tp = sum(c.tp for c in res.type_counts)
        npred = sum(c.n_pred for c in res.type_counts)
        f1[name] = tp / npred if npred else 0.0
    assert set(f1) == {"bpe", "unigram", "unigram_hard", "unigram_soft", "unigram_zwnj_norm"}


def test_hard_decoding_respects_oracle_boundaries(small_ds: Dataset, run_cfg: dict) -> None:
    analyzer = build_analyzer(small_ds)
    pipe = make_pipeline(run_cfg["tokenizer_cfgs"]["unigram_hard"], 120, analyzer)
    pipe.train(small_ds.splits["train"][:200])
    from morphtok.data.normalize import tokens_to_stripped_boundaries

    for line in small_ds.splits["dev"][:20]:
        for pw, toks in pipe.encode_line(line):
            stripped = strip_format(pw.canonical)[0]
            gold = set(small_ds.gold[stripped].boundaries)
            assert gold <= tokens_to_stripped_boundaries(pw, toks)


def test_oracle_refuses_real_data(small_ds: Dataset) -> None:
    import copy

    real = copy.copy(small_ds)
    real.cfg = copy.copy(small_ds.cfg)
    real.cfg.synthetic = False
    with pytest.raises(ValueError):
        build_analyzer(real)


def test_oracle_perturbation_is_deterministic() -> None:
    gold = {"abcdef": (2, 4)}
    a = SyntheticOracleAnalyzer(gold, p_delete=0.5, seed=3)
    assert a.analyze("abcdef") == a.analyze("abcdef")
    assert SyntheticOracleAnalyzer(gold, coverage=0.0).analyze("abcdef") == []


def test_tokenizer_roundtrip() -> None:
    counts = Counter({"abab": 5, "abc": 3, "bca": 2})
    b = BPETokenizer(6)
    b.train(counts)
    b2 = tokenizer_from_dict(b.to_dict())
    for w in counts:
        assert b2.encode_word(w) == b.encode_word(w)


def test_registry_and_objectives_validate() -> None:
    reg = load_registry()
    assert len(reg) >= 7
    fams = {s.family for s in reg}
    assert {"A", "B", "C", "D", "E", "F", "G"} <= fams
    objs = load_objectives()
    assert {"A", "B", "C", "D", "E", "F", "G"} <= set(objs)
    assert all(o.status != "contribution" for o in objs.values())


def test_registry_rejects_incomplete_spec() -> None:
    spec = ExperimentSpec(
        exp_id="X", family="A", hypothesis="H1", gate=0, design="paired", uncertainty="u",
        competing_explanations=["only one"], distinguishing_observation="d", controlled=["v"],
        nuisance=[], baselines=[], intervention="i", primary_metric="m", secondary_metrics=[],
        seeds=[0], expected_outcomes={"only one": "x"}, falsification="f", abandon_if="a",
        followups={"r": "f"},
    )  # fmt: skip
    with pytest.raises(SpecError):
        spec.validate()


def test_novelty_screen_gate() -> None:
    s = NoveltyScreen()
    assert not s.may_claim_novelty()
    assert len(s.incomplete_steps()) == 7


def test_result_record_and_ledger(tmp_path) -> None:  # type: ignore[no-untyped-def]
    rec = new_record("SYN-test", 0, {"a": 1}, {"name": "synthetic"}, synthetic=True)
    assert validate_record(rec) == []
    p = finalise(rec, tmp_path)
    assert p.exists()
    ledger = (tmp_path / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(ledger) == 1 and '"experiment_id": "SYN-test"' in ledger[0]
    bad = new_record("REAL-x", 0, {}, {}, synthetic=True)
    bad["status"] = "ok"
    assert any("SYN" in p for p in validate_record(bad))


def test_followups_fire_only_on_measured_patterns() -> None:
    assert propose_followups("P", {}, synthetic=True) == []
    fd = {"delta": -0.2, "ci_low": -0.3, "ci_high": -0.1}
    f1d = {"delta": 0.0, "ci_low": -0.02, "ci_high": 0.02}
    out = propose_followups("P", {"fertility_delta": fd, "f1_delta": f1d}, synthetic=True)
    assert len(out) == 1 and out[0].status == "proposed"
    assert out[0].literature_verification_status == "unverified"


def test_custom_spec_generates_without_zwnj() -> None:
    c = generate(SyntheticSpec(n_lines=20, p_zwnj_morph=0.0, p_zwnj_other=0.0, p_zwj=0.0))
    assert len(c.lines) == 20
    assert all("‌" not in ln for ln in c.lines)


def test_incremental_bpe_matches_naive_reference() -> None:
    import random

    from morphtok.tokenizers.baselines import _reference_merges

    rng = random.Random(7)
    # many ties: small alphabet, repeated words, uniform counts
    words = {
        "".join(rng.choice("abc") for _ in range(rng.randint(1, 7))): rng.choice([1, 1, 2])
        for _ in range(300)
    }
    fixture = (FIXTURE / "SYNTHETIC_corpus.txt").read_text(encoding="utf-8").split()[:3000]
    for counts in (words, Counter(fixture)):
        n_chars = len({c for w in counts for c in w})
        b = BPETokenizer(n_chars + 120)
        b.train(counts)
        assert b.merges == _reference_merges(counts, len(b.merges))
        assert b.vocab_size == n_chars + 120 or b.warnings
