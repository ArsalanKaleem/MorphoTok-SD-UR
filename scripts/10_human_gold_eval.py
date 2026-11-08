"""Re-score the trained pilot tokenizers against native-speaker (HUMAN) boundary gold.

For every model in the pilot manifest, encode each human-gold word and compute boundary
P/R/F1 against (a) the human gold and (b) the silver labels for the *same* words, so the
two evaluations are directly comparable. Paired comparisons vs ``unigram`` use a
word-level paired bootstrap per seed and a t-interval over seed means.

Writes metric-only outputs (no corpus text) to ``results/human_gold/``.

    python scripts/10_human_gold_eval.py --config configs/run/pilot_wiki.yaml --data sindhi \
        --human data/gold/sd_human_dev.tsv
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from morphtok.data.loaders import load_gold
from morphtok.data.normalize import tokens_to_stripped_boundaries
from morphtok.eval.morph_boundary import f1_of_counts, prf, sum_counts, word_counts
from morphtok.eval.stats import aggregate_seeds, paired_bootstrap
from morphtok.experiments.runner import (
    REPO_ROOT,
    build_analyzer,
    cli,
    exp_id,
    load_dataset,
    make_pipeline,
)
from morphtok.tokenizers.baselines import tokenizer_from_dict

COMPARE = ["unigram_hard_trainonly", "unigram_soft_trainonly", "unigram_hard", "unigram_soft",
           "bpe", "char", "unigram_zwnj_norm"]  # fmt: skip


def _args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--human", required=True, help="human gold TSV from scripts/ingest_review.py")


def read_human(path: Path) -> dict[str, set[int]]:
    """``word -> boundaries`` (stripped coordinates)."""
    out: dict[str, set[int]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        word, bounds, _source, _split = line.split("\t")
        out[word] = {int(x) for x in bounds.split(",") if x}
    return out


def f1_stat(counts: list) -> float:
    """Micro boundary F1 of a resample (0 when undefined)."""
    f = f1_of_counts(counts)
    return f if f is not None else 0.0


def t_ci(xs: list[float]) -> tuple[float, float, float]:
    """Mean and 95% t-interval over seeds (n=3 -> t=4.303)."""
    tcrit = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776}
    m = statistics.fmean(xs)
    if len(xs) < 2:
        return m, m, m
    h = tcrit.get(len(xs), 2.0) * statistics.stdev(xs) / len(xs) ** 0.5
    return m, m - h, m + h


def main() -> int:
    """Score every manifest model on human and silver gold for the same words."""
    args, run, out = cli(__doc__ or "", _args)
    ds = load_dataset(run)
    human = read_human(Path(args.human) if Path(args.human).is_absolute() else REPO_ROOT / args.human)
    silver_all = load_gold(ds.cfg)
    words = sorted(w for w in human if w in silver_all)
    missing = sorted(set(human) - set(words))
    silver = {w: set(silver_all[w].boundaries) for w in words}
    hum = {w: human[w] for w in words}

    manifest = json.loads((out / exp_id("models", ds) / "manifest.json").read_text(encoding="utf-8"))
    analyzer = build_analyzer(ds)
    per: dict[tuple[str, int, int], dict[str, list]] = {}
    for m in manifest:
        name, vocab, seed = m["tokenizer"], int(m["vocab"]), int(m["seed"])
        pipe = make_pipeline(run["tokenizer_cfgs"][name], vocab, analyzer)
        pipe.tokenizer = tokenizer_from_dict(json.loads((out / m["path"]).read_text(encoding="utf-8")))
        hc, sc = [], []
        for w in words:
            pw, toks = pipe.encode_word(w)
            p = tokens_to_stripped_boundaries(pw, toks)
            hc.append(word_counts(p, hum[w]))
            sc.append(word_counts(p, silver[w]))
        per[(name, vocab, seed)] = {"human": hc, "silver": sc}

    # silver labels themselves, scored as a "system" against human gold
    silver_as_sys = prf(sum_counts(word_counts(silver[w], hum[w]) for w in words))

    vocabs = sorted({k[1] for k in per})
    seeds = sorted({k[2] for k in per})
    systems = sorted({k[0] for k in per})
    lines = [
        f"# Human-gold re-score ({ds.cfg.language}, dev, {len(words)} words; "
        f"{len(missing)} human words without a silver entry skipped)",
        "",
        "Human gold: native-speaker review (data/gold/*_human_dev.tsv). Silver: lemma-derived labels",
        "for the same words. All words are dev-split, i.e. lemmas unseen by train-only supervision.",
        "",
        f"Silver labels vs human gold: P={silver_as_sys['precision']:.3f} R={silver_as_sys['recall']:.3f} "
        f"F1={silver_as_sys['f1']:.3f}",
        "",
        "## Boundary F1 (mean ± sd over seeds)",
        "",
        "| system | V | F1 vs human | P vs human | R vs human | F1 vs silver |",
        "|---|---|---|---|---|---|",
    ]
    summary: dict = {"n_words": len(words), "silver_vs_human": silver_as_sys, "systems": {}, "deltas": {}}
    for v in vocabs:
        for s in systems:
            hs = [prf(sum_counts(per[(s, v, sd)]["human"])) for sd in seeds if (s, v, sd) in per]
            ss = [prf(sum_counts(per[(s, v, sd)]["silver"])) for sd in seeds if (s, v, sd) in per]

            def ms(rows: list[dict], key: str) -> str:
                a = aggregate_seeds([r[key] for r in rows])
                return f"{a['mean']:.3f}±{(a['sd'] or 0):.3f}"

            lines.append(
                f"| {s} | {v} | {ms(hs, 'f1')} | {ms(hs, 'precision')} | {ms(hs, 'recall')} | {ms(ss, 'f1')} |"
            )
            summary["systems"][f"{s}@{v}"] = {
                "human": {
                    k: aggregate_seeds([r[k] for r in hs])["mean"] for k in ("precision", "recall", "f1")
                },
                "silver_f1": aggregate_seeds([r["f1"] for r in ss])["mean"],
            }
    lines += ["", "## Paired F1 difference vs `unigram` (system − unigram)", "",
              "Per-seed word-level paired bootstrap (1000 resamples); `seeds` = 95% t-interval over the 3 seed deltas.",
              "", "| system | V | gold | per-seed Δ [95% CI] | seeds: mean [95% CI] | sign agrees with silver? |",
              "|---|---|---|---|---|---|"]  # fmt: skip
    for v in vocabs:
        for s in COMPARE:
            if not all((s, v, sd) in per for sd in seeds):
                continue
            means = {}
            cells = {}
            for g in ("human", "silver"):
                ds_ = []
                txt = []
                for sd in seeds:
                    r = paired_bootstrap(
                        per[("unigram", v, sd)][g], per[(s, v, sd)][g], f1_stat, n_boot=1000, seed=sd
                    )
                    ds_.append(r["delta"])
                    txt.append(f"{r['delta']:+.3f} [{r['ci_low']:+.3f}, {r['ci_high']:+.3f}]")
                means[g] = t_ci(ds_)
                cells[g] = "; ".join(txt)
            for g in ("human", "silver"):
                m, lo, hi = means[g]
                agree = "yes" if (means["human"][0] > 0) == (means["silver"][0] > 0) else "**no**"
                lines.append(
                    f"| {s} | {v} | {g} | {cells[g]} | {m:+.3f} [{lo:+.3f}, {hi:+.3f}] | {agree if g == 'human' else ''} |"
                )
                summary["deltas"][f"{s}@{v}:{g}"] = {"mean": m, "t_ci": [lo, hi]}
    text = "\n".join(lines) + "\n"
    print(text)
    dest = REPO_ROOT / "results" / "human_gold"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"report_{ds.cfg.language}.md").write_text(text, encoding="utf-8")
    (dest / f"summary_{ds.cfg.language}.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"wrote {dest.relative_to(REPO_ROOT)}/report_{ds.cfg.language}.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
