"""Evaluate the full-corpus scale-up (PREREG.md §10, Amendment 3).

For every model in ``runs/<LANG>-<lang>_full-models/manifest.json``: boundary P/R/F1 on all
dev and test silver types (held-out lemmas) and, for Sindhi, on the native-reviewed dev
words; fertility on a seeded sample of 5,000 dev lines. Contrast
``unigram_hard_trainonly − unigram`` per V: per-seed deltas, mean and 95% t-interval over
seeds, verdict by the §10 rule. Writes ``results/scale_full/report_<lang>.md`` and
``summary_<lang>.json`` (metric-only).

    python scripts/16_scale_eval.py --config configs/run/scale_full.yaml --data sindhi_full \
        --human data/gold/sd_human_dev.tsv
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from morphtok.data.normalize import tokens_to_stripped_boundaries
from morphtok.eval.fertility import fertility
from morphtok.eval.morph_boundary import prf, sum_counts, word_counts
from morphtok.experiments.runner import (
    REPO_ROOT,
    build_analyzer,
    cli,
    evaluate,
    exp_id,
    load_dataset,
    make_pipeline,
)
from morphtok.tokenizers.baselines import tokenizer_from_dict

T95 = 4.302652729911275  # t(0.975, df=2): three seeds
MIN_GAIN, MAX_FERT, N_FERT_LINES = 0.010, 0.05, 5000


def _args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--human", default=None, help="native-reviewed dev gold TSV (optional)")


def read_human(path: Path) -> dict[str, set[int]]:
    """``word -> boundaries`` from ingest_review.py output."""
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            w, b, _s, _sp = line.split("\t")
            out[w] = {int(x) for x in b.split(",") if x}
    return out


def ci(xs: list[float]) -> tuple[float, float, float]:
    """Mean and 95% t-interval over three seeds."""
    m = statistics.fmean(xs)
    h = T95 * statistics.stdev(xs) / math.sqrt(len(xs)) if len(xs) == 3 else float("nan")
    return m, m - h, m + h


def main() -> int:
    """Score all models, then write the report."""
    args, run, out = cli(__doc__ or "", _args)
    ds = load_dataset(run)
    lang = ds.cfg.language
    manifest = json.loads((out / exp_id("models", ds) / "manifest.json").read_text(encoding="utf-8"))
    analyzer = build_analyzer(ds)
    gold = {"dev": ds.gold_for("dev"), "test": ds.gold_for("test")}
    human = read_human(REPO_ROOT / args.human) if args.human else {}
    fert_lines = random.Random(13).sample(ds.splits["dev"], min(N_FERT_LINES, len(ds.splits["dev"])))
    res: dict[tuple[str, int, int], dict] = {}
    for m in manifest:
        name, vocab, seed = m["tokenizer"], int(m["vocab"]), int(m["seed"])
        pipe = make_pipeline(run["tokenizer_cfgs"][name], vocab, analyzer)
        pipe.tokenizer = tokenizer_from_dict(json.loads((out / m["path"]).read_text(encoding="utf-8")))
        cache: dict[str, tuple] = {}
        raw_encode = pipe.encode_word

        def cached(w: str, cache: dict = cache, raw_encode=raw_encode) -> tuple:
            if w not in cache:
                cache[w] = raw_encode(w)
            return cache[w]

        pipe.encode_word = cached  # type: ignore[method-assign]
        r: dict = {}
        for split in ("dev", "test"):
            o = evaluate(pipe, fert_lines if split == "dev" else [], gold[split], None, "all")
            r[split] = prf(sum_counts(o.type_counts))
            r[f"{split}_counts"] = o.type_counts
            if split == "dev":
                r["fertility"] = fertility(o.line_units)
        if human:
            hc = [
                word_counts(tokens_to_stripped_boundaries(*pipe.encode_word(w)), b)
                for w, b in sorted(human.items())
            ]
            r["human"] = prf(sum_counts(hc))
        res[(name, vocab, seed)] = r
        print(f"{name} V{vocab} s{seed}: dev F1 {r['dev']['f1']:.4f} test F1 {r['test']['f1']:.4f}"
              + (f" human F1 {r['human']['f1']:.4f}" if human else "") + f" fert {r['fertility']:.4f}", flush=True)  # fmt: skip

    vocabs = sorted({k[1] for k in res})
    n_lines = {k: len(v) for k, v in ds.splits.items()}
    lines = [f"# Full-corpus scale-up ({lang}; PREREG.md §10)", "",
             f"Corpus: {ds.cfg.corpus_path} — lines per split {n_lines}. Gold types: dev "
             f"{len(gold['dev'])}, test {len(gold['test'])}" + (f", native dev words {len(human)}" if human else "")
             + f". Fertility on {len(fert_lines):,} sampled dev lines.", "",
             "| V | gold | unigram F1 | hard train-only F1 | ΔF1 per seed | mean ΔF1 [95% t-CI] | Δ tok/word | verdict |",
             "|---|---|---|---|---|---|---|---|"]  # fmt: skip
    summary: dict = {"lang": lang, "lines": n_lines, "rows": []}
    golds = ["dev", "test"] + (["human"] if human else [])
    for v in vocabs:
        f_base = [res[("unigram", v, s)]["fertility"] for s in (0, 1, 2)]
        f_sys = [res[("unigram_hard_trainonly", v, s)]["fertility"] for s in (0, 1, 2)]
        dfert = statistics.fmean(b - a for a, b in zip(f_base, f_sys, strict=True)) / statistics.fmean(f_base)
        for g in golds:
            base = [res[("unigram", v, s)][g]["f1"] for s in (0, 1, 2)]
            sys_ = [res[("unigram_hard_trainonly", v, s)][g]["f1"] for s in (0, 1, 2)]
            d = [b - a for a, b in zip(base, sys_, strict=True)]
            m, lo, hi = ci(d)
            if g == "dev":
                verdict = (
                    "**replicates**"
                    if m >= MIN_GAIN and lo > 0 and dfert <= MAX_FERT
                    else "**does not replicate**"
                )
            else:
                verdict = "secondary" + (" (CI excludes 0)" if lo > 0 or hi < 0 else "")
            label = {
                "dev": "dev silver (primary)",
                "test": "test silver (non-confirmatory)",
                "human": "native dev",
            }[g]
            per_seed = ", ".join(f"{x:+.4f}" for x in d)
            lines.append(f"| {v} | {label} | {statistics.fmean(base):.4f} | {statistics.fmean(sys_):.4f} | "
                         f"{per_seed} | {m:+.4f} [{lo:+.4f}, {hi:+.4f}] | {dfert:+.2%} | {verdict} |")  # fmt: skip
            summary["rows"].append({"vocab": v, "gold": g, "base_f1": base, "sys_f1": sys_, "delta": d,
                                    "mean": m, "ci": [lo, hi], "rel_fertility": dfert})  # fmt: skip
    text = "\n".join(lines) + "\n"
    print(text)
    dest = REPO_ROOT / "results" / "scale_full"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"report_{lang}.md").write_text(text, encoding="utf-8")
    (dest / f"summary_{lang}.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
