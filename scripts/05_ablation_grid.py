"""Staged one-factor-at-a-time ablations around a base condition (Families B, C, E).

Stage 1  lambda sensitivity (includes lambda = 0 and a large lambda, compared with the
         hard condition to check the hard limit empirically);
Stage 2  confidence -> penalty mapping (confidence-weighted vs uniform, Objective C);
Stage 3  analyzer degradation (coverage reduction, boundary deletion/insertion);
Stage 4  negative control: random boundaries with the analyzer's coverage and count;
Stage 5  sampling stability (Family E) for the base model.

All selection happens on **dev**. The grid size is capped by ``ablations.max_conditions``
so that no unplanned combinatorial search can run from this script.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from morphtok.data.loaders import DataUnavailableError
from morphtok.data.normalize import split_words, strip_format
from morphtok.eval.morph_boundary import prf, sum_counts
from morphtok.eval.stats import aggregate_seeds
from morphtok.experiments.followups import propose_followups, save_followups
from morphtok.experiments.results import finalise, new_record
from morphtok.experiments.runner import (
    SYNTHETIC_BANNER,
    build_analyzer,
    cli,
    evaluate,
    exp_id,
    fmt,
    load_dataset,
    make_pipeline,
    mean_sd,
    print_table,
    train_lines_for_seed,
)
from morphtok.tokenizers.lattice_unigram import UnigramModel
from morphtok.tokenizers.sampling import sampling_stability


def main() -> int:
    """Run the capped OFAT grid and print one table per stage."""
    _, run, out = cli(__doc__ or "")
    try:
        ds = load_dataset(run)
    except DataUnavailableError as e:
        print(f"ABLATIONS SKIPPED: {e}")
        return 2
    if ds.synthetic:
        print(SYNTHETIC_BANNER)
    ab = run["ablations"]
    base_name = ab["base"]
    base_cfg = run["tokenizer_cfgs"][base_name]
    vocab = int(ab["vocab_size"])
    seeds = ab["seeds"]
    conditions: list[tuple[str, str, dict, dict]] = []  # (stage, label, tok overrides, analyzer overrides)
    for lam in ab["lambda_sweep"]:
        conditions.append(("lambda", f"lambda={lam}", {"lambda": lam}, {}))
    conditions.append(("lambda", "hard", {**run["tokenizer_cfgs"]["unigram_hard"]}, {}))
    for pm in ab["penalty_mappings"]:
        sup = {**base_cfg.get("supervision", {}), "penalty": pm}
        conditions.append(("penalty", f"penalty={pm}", {"supervision": sup}, {}))
    for pert in ab["analyzer_perturbations"]:
        label = "cov{coverage}_del{p_delete}_ins{p_insert}".format(**pert)
        conditions.append(("analyzer", label, {}, dict(pert)))
    conditions.append(("negative_control", "random boundaries", {}, {"random_control": True}))
    conditions.append(
        ("negative_control", "no analyzer (plain unigram)", {**run["tokenizer_cfgs"]["unigram"]}, {})
    )
    if len(conditions) > int(ab["max_conditions"]):
        print(f"Refusing: {len(conditions)} conditions exceeds max_conditions={ab['max_conditions']}")
        return 2
    print(
        f"{len(conditions)} conditions x {len(seeds)} seeds at V={vocab}, base={base_name}, selection on dev"
    )
    dev = ds.splits["dev"]
    gold = ds.gold_for("dev")
    results: dict[str, list[float | None]] = {}
    stage_of: dict[str, str] = {}
    base_model: UnigramModel | None = None
    for stage, label, tok_over, an_over in conditions:
        analyzer = build_analyzer(ds, an_over or None)
        eid = exp_id(f"ABL-{stage}-{label}", ds)
        stage_of[label] = stage
        results[label] = []
        for seed in seeds:
            pipe = make_pipeline(base_cfg, vocab, analyzer, overrides=tok_over)
            rec = new_record(eid, seed, {"run": run, "tok_over": tok_over, "an_over": an_over}, ds.describe(),
                             ds.synthetic, vocab, pipe.policy.describe(),
                             {"name": base_name, "version": pipe.tokenizer.version})  # fmt: skip
            try:
                pipe.train(train_lines_for_seed(ds, seed, float(run["train_fraction"])))
                res = evaluate(pipe, dev, gold, gold_scope=run["eval_cfg"].get("gold_scope", "corpus"))
            except Exception as e:  # noqa: BLE001
                finalise(rec, out, "failed", e)
                results[label].append(None)
                continue
            m = prf(sum_counts(res.type_counts))
            rec["metrics"] = {**m, "mean_token_len": res.mean_token_len}
            finalise(rec, out)
            results[label].append(m["f1"])
            if label == f"lambda={base_cfg.get('lambda')}" and seed == seeds[0]:
                base_model = getattr(pipe.tokenizer, "model", None)
    rows = [
        [stage_of[k], k, mean_sd(v), f"{sum(x is not None for x in v)}/{len(v)}"] for k, v in results.items()
    ]
    print("\nDev boundary F1 by condition (mean±sd over seeds)")
    table = print_table(["stage", "condition", "F1", "ok"], rows)

    perts = [c for c in conditions if c[0] == "analyzer"]
    # Slope of F1 against boundary-deletion rate, using only full-coverage, no-insertion conditions.
    del_only = [c for c in perts if c[3].get("coverage", 1.0) == 1.0 and c[3].get("p_insert", 0.0) == 0.0]
    clean_c = [c for c in del_only if c[3].get("p_delete", 0.0) == 0.0]
    clean = aggregate_seeds(results[clean_c[0][1]])["mean"] if clean_c else None
    deletes = [(c[3].get("p_delete", 0.0), aggregate_seeds(results[c[1]])["mean"]) for c in del_only]
    deletes = [(p, f) for p, f in deletes if f is not None]
    slope = None
    if clean is not None and len({p for p, _ in deletes}) > 1:
        pmax, fmax = max(deletes)
        slope = (fmax - clean) / pmax if pmax > 0 else None
    print(f"\nF1 change per unit boundary-deletion rate: {fmt(slope)}")
    big = f"lambda={max(ab['lambda_sweep'])}"
    print(
        f"Hard-limit check: {big} F1 {mean_sd(results.get(big, []))} vs hard {mean_sd(results.get('hard', []))}"
    )

    srows = []
    if base_model is not None:
        rng = random.Random(0)
        words = sorted({strip_format(w)[0] for ln in dev for w in split_words(ln)})
        sample = rng.sample(words, min(int(ab["sampling"]["n_words"]), len(words)))
        for alpha in ab["sampling"]["alphas"]:
            stats = [
                sampling_stability(base_model, w, int(ab["sampling"]["n_samples"]), 0, alpha) for w in sample
            ]
            srows.append([str(alpha), fmt(sum(s.n_distinct for s in stats) / len(stats), 2),
                          fmt(sum(s.viterbi_agreement for s in stats) / len(stats)),
                          fmt(sum(s.exact_entropy for s in stats) / len(stats))])  # fmt: skip
        print(f"\nSampling stability of the base model ({len(sample)} dev words, unconstrained lattice)")
        print_table(["alpha", "distinct segs", "Viterbi agreement", "exact entropy (nats)"], srows)
    fus = propose_followups(exp_id("ABL-grid", ds), {"perturbation_slope": slope}, ds.synthetic)
    save_followups(fus, out / "followups.jsonl")
    sdir = out / exp_id("ABL-summary", ds)
    sdir.mkdir(parents=True, exist_ok=True)
    (sdir / "table.txt").write_text(table + "\n", encoding="utf-8")
    (sdir / "results.json").write_text(
        json.dumps({"f1": results, "slope": slope}, indent=1), encoding="utf-8"
    )
    print(f"\nsaved {sdir}; {len(fus)} follow-up hypotheses proposed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
