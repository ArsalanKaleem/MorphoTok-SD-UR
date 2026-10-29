"""Intrinsic evaluation of trained tokenizers (Gates 0 and 3 analyses).

Reports, per vocabulary size: boundary P/R/F1 and exact match over gold types,
fertility, tokens/char and mean token length (mean±sd over seeds); paired
comparisons against the reference system (bootstrap CIs per seed, t-CI over seeds,
approximate-randomization p, Cohen's d_z over seeds); soft vs hard (Gate 3); the
normalization share of the fertility difference (H1); and frequency- and
coverage-stratified F1. Evaluates on ``dev`` unless ``--split test --final``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from morphtok.data.loaders import DataUnavailableError, resolve
from morphtok.eval.exact_match import exact_match
from morphtok.eval.fertility import fertility, tokens_per_char
from morphtok.eval.morph_boundary import f1_of_counts, prf, sum_counts
from morphtok.eval.paradigm import paradigm_coherence
from morphtok.eval.rare_words import frequency_key, stratified_boundary_metrics
from morphtok.eval.stats import (
    aggregate_seeds,
    approximate_randomization,
    cohens_dz,
    paired_bootstrap,
)
from morphtok.experiments.followups import propose_followups, save_followups
from morphtok.experiments.results import finalise, new_record
from morphtok.experiments.runner import (
    SYNTHETIC_BANNER,
    IntrinsicOutput,
    build_analyzer,
    cli,
    evaluate,
    exp_id,
    fmt,
    load_dataset,
    make_pipeline,
    mean_sd,
    print_table,
    stripped_counts,
    train_lines_for_seed,
)
from morphtok.provenance import prereg_status
from morphtok.tokenizers.baselines import tokenizer_from_dict


def _args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--split", default=None, choices=["dev", "test"])
    ap.add_argument("--final", action="store_true", help="required to evaluate on test")


def fert_stat(units: list) -> float:
    """Fertility for bootstrap resamples."""
    f = fertility(units)
    return f if f is not None else 0.0


def ci_str(d: dict[str, float] | None, nd: int = 4) -> str:
    """``delta [lo, hi]``."""
    if not d:
        return "n/a"
    return f"{d['delta']:+.{nd}f} [{d['ci_low']:+.{nd}f}, {d['ci_high']:+.{nd}f}]"


def main() -> int:
    """Evaluate every model in the manifest and print the reports."""
    args, run, out = cli(__doc__ or "", _args)
    try:
        ds = load_dataset(run)
    except DataUnavailableError as e:
        print(f"INTRINSIC EVAL SKIPPED: {e}")
        return 2
    ev = run["eval_cfg"]
    split = args.split or ev.get("eval_split", "dev")
    if split == "test" and not args.final:
        print("Refusing to evaluate on test without --final (test is reserved for the preregistered report).")
        return 2
    if split == "test" and not ds.synthetic and not prereg_status()["frozen"]:
        print("Refusing to evaluate on real test data: preregistration is not frozen (make prereg-status).")
        return 2
    if ds.synthetic:
        print(SYNTHETIC_BANNER)
    manifest_path = out / exp_id("models", ds) / "manifest.json"
    if not manifest_path.exists():
        print(f"No manifest at {manifest_path}; run `make tokenizer` first.")
        return 2
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    analyzer = build_analyzer(ds)
    lines = ds.splits[split]
    gold = ds.gold_for(split)
    nboot = int(ev["bootstrap"]["n_boot"])
    nperm = int(ev["randomization"]["n_perm"])
    ref = ev.get("reference_system", "unigram")
    paradigms: dict[str, set[str]] = {}
    ppath = resolve(ds.cfg.paradigms_path)
    if ppath is not None and ppath.exists():
        raw = json.loads(ppath.read_text(encoding="utf-8"))
        paradigms = {lem: set(v["forms"]) for lem, v in raw.items() if v["split"] == split}
    results: dict[tuple[str, int, int], tuple[dict, IntrinsicOutput]] = {}
    for m in manifest:
        name, vocab, seed = m["tokenizer"], int(m["vocab"]), int(m["seed"])
        pipe = make_pipeline(run["tokenizer_cfgs"][name], vocab, analyzer)
        pipe.tokenizer = tokenizer_from_dict(json.loads((out / m["path"]).read_text(encoding="utf-8")))
        rec = new_record(exp_id(f"EVAL-{name}-V{vocab}-{split}", ds), seed, {"run": run, "split": split},
                         ds.describe(), ds.synthetic, vocab, pipe.policy.describe(),
                         {"name": name, "version": pipe.tokenizer.version, "model_run_id": m["run_id"]})  # fmt: skip
        try:
            res = evaluate(
                pipe,
                lines,
                gold,
                analyzer if analyzer.is_configured else None,
                ev.get("gold_scope", "corpus"),
            )
        except Exception as e:  # noqa: BLE001
            finalise(rec, out, "failed", e)
            continue
        met = {**prf(sum_counts(res.type_counts)), "exact_match": exact_match(res.type_preds, res.type_golds),
               "fertility": fertility(res.line_units), "tokens_per_char": tokens_per_char(res.line_units),
               "mean_token_len": res.mean_token_len, "n_gold_types": len(res.type_words),
               "decode_fallbacks": getattr(pipe.tokenizer, "decode_fallbacks", 0)}  # fmt: skip
        if paradigms:
            pc = paradigm_coherence(paradigms, lambda w, pipe=pipe: pipe.encode_word(w)[1])
            met.update({f"paradigm_{k}": v for k, v in pc.items()})
        rec["metrics"] = met
        finalise(rec, out)
        results[(name, vocab, seed)] = (met, res)

    names = list(dict.fromkeys(m["tokenizer"] for m in manifest))
    vocabs = sorted({int(m["vocab"]) for m in manifest})
    seeds = sorted({int(m["seed"]) for m in manifest})
    rows = []
    for v in vocabs:
        for n in names:
            ms = [results[(n, v, s)][0] if (n, v, s) in results else None for s in seeds]
            ok = [x for x in ms if x]
            rows.append([str(v), n, mean_sd([x["f1"] for x in ok]), mean_sd([x["precision"] for x in ok]),
                         mean_sd([x["recall"] for x in ok]), mean_sd([x["exact_match"] for x in ok]),
                         mean_sd([x["fertility"] for x in ok]), mean_sd([x["tokens_per_char"] for x in ok]),
                         mean_sd([x["mean_token_len"] for x in ok], 2),
                    mean_sd([x.get("paradigm_coherence") for x in ok]), f"{len(ok)}/{len(ms)}"])  # fmt: skip
    print(
        f"\nIntrinsic metrics on {split} (gold types: boundary metrics; lines: efficiency), mean±sd over seeds"
    )
    t1 = print_table(
        ["V", "system", "F1", "P", "R", "exact", "tok/word", "tok/char", "tok len", "paradigm coh.", "ok"],
        rows,
    )

    def compare(a: str, b: str, v: int) -> dict[str, object]:
        f1d, fd, ar = [], [], None
        for s in seeds:
            if (a, v, s) not in results or (b, v, s) not in results:
                continue
            ra, rb = results[(a, v, s)][1], results[(b, v, s)][1]
            if ra.type_words == rb.type_words and ra.type_words:
                f1d.append(paired_bootstrap(ra.type_counts, rb.type_counts, f1_of_counts, nboot, s))
                if ar is None:
                    ar = approximate_randomization(ra.type_counts, rb.type_counts, f1_of_counts, nperm, s)
            fd.append(paired_bootstrap(ra.line_units, rb.line_units, fert_stat, nboot, s))
        return {"f1": f1d, "fert": fd, "ar_seed0": ar,
                "f1_over_seeds": aggregate_seeds([d["delta"] for d in f1d]),
                "fert_over_seeds": aggregate_seeds([d["delta"] for d in fd]),
                "dz_f1": cohens_dz([d["delta"] for d in f1d])}  # fmt: skip

    def over(agg: dict) -> str:
        if agg["mean"] is None:
            return "n/a"
        if agg["ci_low"] is None:
            return f"{agg['mean']:+.4f}"
        return f"{agg['mean']:+.4f} [{agg['ci_low']:+.4f}, {agg['ci_high']:+.4f}]"

    comps: dict[str, dict] = {}
    rows = []
    pairs = [(ref, n) for n in names if n != ref]
    if "unigram_hard" in names and "unigram_soft" in names:
        pairs.append(("unigram_hard", "unigram_soft"))
    for v in vocabs:
        for a, b in pairs:
            c = compare(a, b, v)
            comps[f"{b}_minus_{a}_V{v}"] = c
            rows.append([str(v), f"{b} - {a}", ci_str(c["f1"][0] if c["f1"] else None),
                         over(c["f1_over_seeds"]), fmt(c["dz_f1"], 2),
                         fmt(c["ar_seed0"]["p_value"] if c["ar_seed0"] else None),
                         ci_str(c["fert"][0] if c["fert"] else None), over(c["fert_over_seeds"])])  # fmt: skip
    print(
        "\nPaired comparisons (B - A). Seed-0 bootstrap 95% CI; 'over seeds' = mean [t-CI] of per-seed deltas"
    )
    t2 = print_table(["V", "contrast", "ΔF1 seed0", "ΔF1 over seeds", "d_z", "AR p", "Δtok/word seed0",
                      "Δtok/word over seeds"], rows)  # fmt: skip

    print(
        "\nH1 -- normalization share of the fertility difference (per seed: Δ(zwnj_norm−ref) / Δ(soft−ref))"
    )
    share_rows = []
    shares_by_v: dict[int, dict] = {}
    for v in vocabs:
        shares = []
        for s in seeds:
            keys = [(ref, v, s), ("unigram_zwnj_norm", v, s), ("unigram_soft", v, s)]
            if all(k in results for k in keys):
                base = results[keys[0]][0]["fertility"]
                dn = results[keys[1]][0]["fertility"] - base
                dt = results[keys[2]][0]["fertility"] - base
                shares.append(dn / dt if abs(dt) > 1e-12 else None)
        shares_by_v[v] = aggregate_seeds(shares)
        share_rows.append([str(v), mean_sd(shares), str(shares_by_v[v]["n_failed"])])
    print_table(["V", "share (mean±sd)", "undefined seeds"], share_rows)
    print(
        "A share is only interpretable when Δ(soft−ref) is non-zero with a CI excluding 0 (see table above)."
    )

    big = vocabs[-1]
    train_counts = stripped_counts(train_lines_for_seed(ds, seeds[0], float(run["train_fraction"])))
    key = frequency_key(train_counts, ev["frequency_bins"])
    print(f"\nStratified boundary F1 at V={big}, seed {seeds[0]} (train-frequency bins; analyzer coverage)")
    srows = []
    strat: dict[str, object] = {}
    for n in names:
        if (n, big, seeds[0]) not in results:
            continue
        r = results[(n, big, seeds[0])][1]
        fb = stratified_boundary_metrics(r.type_words, r.type_preds, r.type_golds, key)
        cv = stratified_boundary_metrics(r.type_words, r.type_preds, r.type_golds,
                                         lambda w, r=r: "covered" if r.type_covered[r.type_words.index(w)]
                                         else "uncovered")  # fmt: skip
        strat[n] = {"frequency": fb, "coverage": cv}
        cells = [f"{k}:{fmt(x['f1'], 2)}(n={x['n_words']})" for k, x in fb.items()]
        cells += [f"{k}:{fmt(x['f1'], 2)}(n={x['n_words']})" for k, x in cv.items()]
        srows.append([n, "  ".join(cells)])
    print_table(["system", "F1 by stratum"], srows)

    summary_dir = out / exp_id(f"EVAL-summary-{split}", ds)
    summary_dir.mkdir(parents=True, exist_ok=True)
    for v in vocabs:
        c = comps.get(f"unigram_soft_minus_{ref}_V{v}")
        if not c:
            continue
        sh = comps.get(f"unigram_soft_minus_unigram_hard_V{v}")
        soft_f1 = [
            results[("unigram_soft", v, s)][0]["f1"] for s in seeds if ("unigram_soft", v, s) in results
        ]
        summ = {
            "fertility_delta": c["fert"][0] if c["fert"] else None,
            "f1_delta": c["f1"][0] if c["f1"] else None,
            "normalization_share": shares_by_v[v]["mean"],
            "soft_minus_hard_f1": sh["f1"][0] if sh and sh["f1"] else None,
            "seed_sd_f1": aggregate_seeds(soft_f1)["sd"],
        }
        save_followups(propose_followups(exp_id(f"EVAL-soft-vs-{ref}-V{v}", ds), summ, ds.synthetic),
                       out / "followups.jsonl")  # fmt: skip
    (summary_dir / "tables.txt").write_text(t1 + "\n\n" + t2 + "\n", encoding="utf-8")
    (summary_dir / "comparisons.json").write_text(
        json.dumps({"comparisons": comps, "shares": shares_by_v, "stratified": strat}, indent=1, default=str),
        encoding="utf-8",
    )
    print(f"\nsaved {summary_dir}; follow-up hypotheses appended to {out / 'followups.jsonl'}")
    print("Decision thresholds for Gates 0/3 are UNRESOLVED until the pilot (prereg/decision_gates.md).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
