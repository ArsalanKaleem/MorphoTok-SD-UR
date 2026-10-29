"""Shared run logic for the numbered scripts (dataset loading, analyzers, train/eval).

Keeping this in one module guarantees that every script trains and evaluates each
condition identically. Synthetic datasets get experiment IDs prefixed ``SYN-`` and
every printed table carries a SYNTHETIC banner.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from morphtok.analyzers.base import Analyzer, NullAnalyzer
from morphtok.analyzers.confidence import (
    PerturbedAnalyzer,
    RandomBoundaryAnalyzer,
    SupervisionConfig,
)
from morphtok.analyzers.fst_urdu import UrduFSTAnalyzer
from morphtok.analyzers.lemma_derived import LemmaDerivedAnalyzer, load_silver_entries, merge_silver
from morphtok.analyzers.rules_sindhi import SindhiRuleAnalyzer
from morphtok.analyzers.synthetic import SyntheticOracleAnalyzer
from morphtok.config import load_run_config
from morphtok.data.loaders import (
    DatasetConfig,
    GoldEntry,
    load_gold,
    load_lines,
    resolve,
)
from morphtok.data.normalize import (
    NormalizationPolicy,
    ProcessedWord,
    ZwnjPolicy,
    split_words,
    strip_format,
    tokens_to_stripped_boundaries,
)
from morphtok.data.splits import split_lines, subsample
from morphtok.eval.fertility import UnitCounts, unit_counts
from morphtok.eval.morph_boundary import BoundaryCounts, word_counts
from morphtok.eval.stats import aggregate_seeds
from morphtok.provenance import REPO_ROOT
from morphtok.tokenizers.baselines import build_tokenizer
from morphtok.tokenizers.pipeline import TokenizationPipeline

SYNTHETIC_BANNER = (
    "=" * 78 + "\nSYNTHETIC DATA -- integration test of the pipeline only. These numbers are NOT\n"
    "empirical findings about Sindhi or Urdu and must not be reported as such.\n" + "=" * 78
)


@dataclass
class Dataset:
    """A loaded dataset with gold annotations and split assignment."""

    cfg: DatasetConfig
    lines: list[str]
    data_hash: str
    gold: dict[str, GoldEntry]
    splits: dict[str, list[str]] = field(default_factory=dict)

    @property
    def synthetic(self) -> bool:
        """Whether this is the synthetic fixture."""
        return self.cfg.synthetic

    def gold_for(self, split: str) -> dict[str, tuple[int, ...]]:
        """Gold boundaries for one gold split (``dev`` or ``test``)."""
        return {w: e.boundaries for w, e in self.gold.items() if e.split == split}

    def describe(self) -> dict[str, Any]:
        """Provenance block for result records."""
        return {
            "name": self.cfg.name,
            "language": self.cfg.language,
            "synthetic": self.synthetic,
            "corpus_path": self.cfg.corpus_path,
            "sha256": self.data_hash,
            "n_lines": len(self.lines),
            "split_sizes": {k: len(v) for k, v in self.splits.items()},
            "n_gold": len(self.gold),
            "licence": self.cfg.licence,
            "domain": self.cfg.domain,
        }


def exp_id(base: str, ds: Dataset) -> str:
    """Experiment ID with the mandatory ``SYN-`` prefix for synthetic data."""
    if ds.synthetic:
        return f"SYN-{base}"
    lang = ds.cfg.language.upper()
    # default configs (sindhi/urdu) keep the short prefix; variants (web, audit) are named
    return f"{lang}-{base}" if ds.cfg.name in ("sindhi", "urdu") else f"{lang}-{ds.cfg.name}-{base}"


def load_dataset(run_cfg: dict[str, Any]) -> Dataset:
    """Load the run's dataset (raises ``DataUnavailableError`` for missing real data)."""
    cfg = DatasetConfig.load(resolve(run_cfg["data_config_path"]))  # type: ignore[arg-type]
    lines, h = load_lines(cfg)
    ds = Dataset(cfg=cfg, lines=lines, data_hash=h, gold=load_gold(cfg))
    ratios = run_cfg.get("splits", {"train": 0.8, "dev": 0.1, "test": 0.1})
    ds.splits = split_lines(lines, ratios, salt=str(cfg.split.get("salt", "morphtok")))
    return ds


def build_analyzer(ds: Dataset, override: dict[str, Any] | None = None) -> Analyzer:
    """Analyzer from the dataset config (optionally overridden for ablations)."""
    spec = {**ds.cfg.analyzer, **(override or {})}
    kind = spec.get("type", "null")
    if kind == "synthetic_oracle":
        if not ds.synthetic:
            raise ValueError("the synthetic oracle analyzer may only be used with synthetic data")
        oracle: Analyzer = SyntheticOracleAnalyzer(
            gold={w: e.boundaries for w, e in ds.gold.items()},
            coverage=float(spec.get("coverage", 1.0)),
            p_delete=float(spec.get("p_delete", 0.0)),
            p_insert=float(spec.get("p_insert", 0.0)),
            p_shift=float(spec.get("p_shift", 0.0)),
            confidence=float(spec.get("confidence", 0.9)),
            confidence_noise=float(spec.get("confidence_noise", 0.0)),
            seed=int(spec.get("seed", 0)),
        )
        if spec.get("random_control"):
            oracle = RandomBoundaryAnalyzer(oracle, seed=int(spec.get("seed", 0)))
        return oracle
    if kind == "lemma_derived":
        raw_paths = spec.get("silver_path")
        paths = [resolve(p) for p in (raw_paths if isinstance(raw_paths, list) else [raw_paths])]
        paths = [p for p in paths if p is not None and p.exists()]
        if not paths:
            an: Analyzer = NullAnalyzer()
        else:
            entries = merge_silver([load_silver_entries(p) for p in paths])
            an = LemmaDerivedAnalyzer(
                entries,
                use_splits=frozenset(spec.get("use_splits", ["train"])),
                base_confidence=float(spec.get("base_confidence", 0.8)),
                version="silver:" + "+".join(p.name for p in paths),
            )
    elif kind == "sindhi_rules":
        an = SindhiRuleAnalyzer(resolve(spec.get("rules_path")))
    elif kind == "urdu_fst":
        an = UrduFSTAnalyzer(spec.get("command"), version=str(spec.get("version", "unverified")))
    else:
        an = NullAnalyzer()
    if spec.get("random_control"):
        an = RandomBoundaryAnalyzer(an, seed=int(spec.get("seed", 0)))
    if any(k in spec for k in ("coverage", "p_delete", "p_insert")):
        an = PerturbedAnalyzer(
            an,
            coverage=float(spec.get("coverage", 1.0)),
            p_delete=float(spec.get("p_delete", 0.0)),
            p_insert=float(spec.get("p_insert", 0.0)),
            seed=int(spec.get("seed", 0)),
        )
    return an


def policy_from(cfg: dict[str, Any], zwnj_override: str | None = None) -> NormalizationPolicy:
    """Normalization policy from a tokenizer config block."""
    norm = cfg.get("normalization", {})
    return NormalizationPolicy(
        unicode_form=str(norm.get("unicode_form", "NFC")),
        zwnj=ZwnjPolicy(zwnj_override or norm.get("zwnj", "preserve")),
    )


def make_pipeline(
    tok_cfg: dict[str, Any],
    vocab_size: int,
    analyzer: Analyzer | None,
    zwnj_override: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> TokenizationPipeline:
    """Instantiate one condition; analyzers are attached only if the config requires one."""
    cfg = {**tok_cfg, **(overrides or {})}
    tok = build_tokenizer(cfg, vocab_size)
    uses = bool(cfg.get("requires_analyzer", False))
    return TokenizationPipeline(
        policy=policy_from(cfg, zwnj_override),
        tokenizer=tok,
        analyzer=analyzer if uses else None,
        supervision=SupervisionConfig.from_dict(cfg.get("supervision", {})),
    )


def train_lines_for_seed(ds: Dataset, seed: int, fraction: float) -> list[str]:
    """Seeded subsample of the train split (the source of between-seed variation)."""
    return subsample(ds.splits["train"], fraction, seed)


def stripped_counts(lines: Sequence[str]) -> Counter[str]:
    """Frequency of stripped word types (for rare-word strata)."""
    c: Counter[str] = Counter()
    for ln in lines:
        for w in split_words(ln):
            c[strip_format(w)[0]] += 1
    return c


@dataclass
class IntrinsicOutput:
    """Per-unit evaluation outputs, aligned across systems for paired statistics."""

    line_units: list[UnitCounts]
    type_words: list[str]
    type_preds: list[set[int]]
    type_golds: list[set[int]]
    type_counts: list[BoundaryCounts]
    type_covered: list[bool]
    mean_token_len: float | None


def evaluate(
    pipe: TokenizationPipeline,
    lines: Sequence[str],
    gold: dict[str, tuple[int, ...]],
    analyzer_for_coverage: Analyzer | None = None,
    gold_scope: str = "corpus",
) -> IntrinsicOutput:
    """Fertility units (per line) and boundary metrics (per distinct canonical gold type).

    ``gold_scope="corpus"``: gold types are the distinct *raw* word forms in ``lines``
    whose stripped form has a gold entry. ``gold_scope="all"``: every gold type of the
    split is encoded directly as a word (more statistical power; used when gold comes
    from a word list such as lemma-derived silver data, which contains no format
    characters). Types are sorted for alignment across systems.
    """
    units: list[UnitCounts] = []
    seen: dict[str, tuple[ProcessedWord, list[str]]] = {}
    tok_chars = 0
    n_tok = 0
    for ln in lines:
        enc = pipe.encode_line(ln)
        units.append(unit_counts(enc))
        for pw, toks in enc:
            n_tok += len(toks)
            tok_chars += sum(len(strip_format(t)[0]) for t in toks)
            if gold_scope == "corpus" and pw.raw not in seen and strip_format(pw.canonical)[0] in gold:
                seen[pw.raw] = (pw, toks)
    if gold_scope == "all":
        for w in gold:
            seen[w] = pipe.encode_word(w)
    elif gold_scope != "corpus":
        raise ValueError(f"unknown gold_scope {gold_scope!r}")
    words, preds, golds, counts, covered = [], [], [], [], []
    for raw in sorted(seen):
        pw, toks = seen[raw]
        stripped = strip_format(pw.canonical)[0]
        p = tokens_to_stripped_boundaries(pw, toks)
        g = set(gold[stripped])
        words.append(stripped)
        preds.append(p)
        golds.append(g)
        counts.append(word_counts(p, g))
        cov = False
        if analyzer_for_coverage is not None:
            try:
                cov = bool(analyzer_for_coverage.analyze(stripped))
            except Exception:  # noqa: BLE001 - uncovered on any analyzer failure
                cov = False
        covered.append(cov)
    return IntrinsicOutput(
        line_units=units,
        type_words=words,
        type_preds=preds,
        type_golds=golds,
        type_counts=counts,
        type_covered=covered,
        mean_token_len=tok_chars / n_tok if n_tok else None,
    )


def cli(
    description: str, extra: Callable[[argparse.ArgumentParser], None] | None = None
) -> tuple[argparse.Namespace, dict[str, Any], Path]:
    """Common CLI: ``--config``, ``--data``, ``--out``; forces UTF-8 stdout."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--config", default="configs/run/default.yaml")
    ap.add_argument("--data", default=None, help="dataset name or path (overrides run config)")
    ap.add_argument("--out", default=None, help="output directory (default: run config output_dir)")
    if extra:
        extra(ap)
    args = ap.parse_args()
    run_cfg = load_run_config(args.config, args.data)
    out = Path(args.out or run_cfg.get("output_dir", "runs"))
    if not out.is_absolute():
        out = REPO_ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    return args, run_cfg, out


def mean_sd(values: Sequence[float | None], nd: int = 3) -> str:
    """``mean±sd`` over seeds (``n/a`` when nothing succeeded)."""
    agg = aggregate_seeds(values)
    if agg["mean"] is None:
        return "n/a"
    if agg["sd"] is None:
        return f"{agg['mean']:.{nd}f}"
    return f"{agg['mean']:.{nd}f}±{agg['sd']:.{nd}f}"


def fmt(x: float | None, nd: int = 3) -> str:
    """Format a possibly-missing number."""
    return "n/a" if x is None else f"{x:.{nd}f}"


def print_table(headers: list[str], rows: list[list[str]]) -> str:
    """Render a plain-text table (also returned for saving)."""
    widths = [max(len(h), *(len(r[i]) for r in rows)) if rows else len(h) for i, h in enumerate(headers)]
    lines = [" | ".join(h.ljust(w) for h, w in zip(headers, widths, strict=True))]
    lines.append("-+-".join("-" * w for w in widths))
    lines += [" | ".join(c.ljust(w) for c, w in zip(r, widths, strict=True)) for r in rows]
    text = "\n".join(lines)
    print(text)
    return text
