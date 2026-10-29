"""Gate 0: baseline tokenizers x ZWNJ normalization policies at matched vocabulary sizes.

For every (vocab size, tokenizer, policy, seed) the tokenizer is trained on a seeded
subsample of the train split and evaluated on the dev split. The table reports
mean±sd over seeds of fertility (tokens / orthographic word), tokens per stripped
character, mean token length and -- where gold exists -- boundary F1. Paired
bootstrap CIs compare each policy with ``preserve`` for the same tokenizer, vocab
size and seed. Lower fertility alone is not evidence of a better tokenizer.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from morphtok.data.loaders import DataUnavailableError
from morphtok.eval.fertility import fertility, tokens_per_char
from morphtok.eval.morph_boundary import f1_of_counts, prf, sum_counts
from morphtok.eval.stats import aggregate_seeds, paired_bootstrap
from morphtok.experiments.followups import propose_followups, save_followups
from morphtok.experiments.results import finalise, new_record
from morphtok.experiments.runner import (
    SYNTHETIC_BANNER,
    cli,
    evaluate,
    exp_id,
    load_dataset,
    make_pipeline,
    mean_sd,
    print_table,
    train_lines_for_seed,
)


def main() -> int:
    """Run Gate 0 and print the matched-vocabulary table."""
    _, run, out = cli(__doc__ or "")
    try:
        ds = load_dataset(run)
    except DataUnavailableError as e:
        print(f"GATE 0 SKIPPED: {e}")
        return 2
    if ds.synthetic:
        print(SYNTHETIC_BANNER)
    g0 = run["gate0"]
    eval_cfg = run["eval_cfg"]
    gold = ds.gold_for(eval_cfg.get("eval_split", "dev"))
    dev = ds.splits["dev"]
    nboot = int(eval_cfg["bootstrap"]["n_boot"])
    rows: list[list[str]] = []
    comparisons: list[list[str]] = []
    summary: dict[str, object] = {}
    for vocab in run["vocab_sizes"]:
        for tok_name in g0["tokenizers"]:
            tok_cfg = run["tokenizer_cfgs"][tok_name]
            per_policy: dict[str, list] = {}
            for policy in g0["policies"]:
                eid = exp_id(f"G0-{tok_name}-{policy}-V{vocab}", ds)
                per_seed = []
                for seed in run["seeds"]:
                    pipe = make_pipeline(tok_cfg, vocab, analyzer=None, zwnj_override=policy)
                    rec = new_record(eid, seed, {"run": run, "policy": policy}, ds.describe(), ds.synthetic,
                                     vocab, pipe.policy.describe(),
                                     {"name": tok_name, "version": pipe.tokenizer.version})  # fmt: skip
                    try:
                        pipe.train(train_lines_for_seed(ds, seed, float(run["train_fraction"])))
                        res = evaluate(
                            pipe, dev, gold, gold_scope=run["eval_cfg"].get("gold_scope", "corpus")
                        )
                    except Exception as e:  # noqa: BLE001 - failed runs are recorded, not dropped
                        finalise(rec, out, "failed", e)
                        per_seed.append(None)
                        continue
                    m = {
                        "fertility": fertility(res.line_units),
                        "tokens_per_char": tokens_per_char(res.line_units),
                        "mean_token_len": res.mean_token_len,
                        "realised_vocab": pipe.tokenizer.vocab_size,
                        **{f"boundary_{k}": v for k, v in prf(sum_counts(res.type_counts)).items()},
                        "n_gold_types": len(res.type_words),
                    }
                    rec["metrics"] = m
                    if tok_name != "char" and pipe.tokenizer.vocab_size != vocab:
                        rec["warnings"].append(f"vocab NOT matched: {pipe.tokenizer.vocab_size} != {vocab}")
                    finalise(rec, out)
                    per_seed.append((m, res))
                per_policy[policy] = per_seed
                ok = [p for p in per_seed if p is not None]
                vs = {p[0]["realised_vocab"] for p in ok}
                rows.append([
                    str(vocab), tok_name, policy, ",".join(map(str, sorted(vs))),
                    mean_sd([p[0]["fertility"] for p in ok]),
                    mean_sd([p[0]["tokens_per_char"] for p in ok]),
                    mean_sd([p[0]["mean_token_len"] for p in ok], 2),
                    mean_sd([p[0]["boundary_f1"] for p in ok]),
                    f"{len(ok)}/{len(per_seed)}",
                ])  # fmt: skip
            base = per_policy.get("preserve", [])
            for policy, seeds in per_policy.items():
                if policy == "preserve":
                    continue
                fd, f1d = [], []
                for a, b in zip(base, seeds, strict=True):
                    if a is None or b is None:
                        continue
                    fd.append(paired_bootstrap(a[1].line_units, b[1].line_units, fertility_stat, nboot, 0))
                    if a[1].type_words == b[1].type_words and a[1].type_words:
                        f1d.append(
                            paired_bootstrap(a[1].type_counts, b[1].type_counts, f1_of_counts, nboot, 0)
                        )
                key = f"{tok_name}-V{vocab}-{policy}_vs_preserve"
                summary[key] = {"fertility_delta": fd, "f1_delta": f1d,
                                "seed_agg_fertility_delta": aggregate_seeds([d["delta"] for d in fd]),
                                "seed_agg_f1_delta": aggregate_seeds([d["delta"] for d in f1d])}  # fmt: skip
                if fd:
                    d0 = fd[0]
                    f0 = f1d[0] if f1d else None
                    comparisons.append([
                        str(vocab), tok_name, f"{policy} - preserve",
                        f"{d0['delta']:+.4f} [{d0['ci_low']:+.4f}, {d0['ci_high']:+.4f}]",
                        f"{f0['delta']:+.4f} [{f0['ci_low']:+.4f}, {f0['ci_high']:+.4f}]" if f0 else "n/a",
                        mean_sd([d["delta"] for d in fd], 4),
                    ])  # fmt: skip
                    fus = propose_followups(exp_id(f"G0-{key}", ds),
                                            {"fertility_delta": d0, "f1_delta": f0}, ds.synthetic)  # fmt: skip
                    save_followups(fus, out / "followups.jsonl")
    print("\nGate 0 -- matched-vocabulary comparison on the dev split (mean±sd over seeds)")
    table = print_table(
        ["V", "tokenizer", "zwnj policy", "realised V", "tokens/word", "tokens/char", "mean tok len",
         "boundary F1", "ok seeds"], rows)  # fmt: skip
    print("\nPaired differences vs preserve (seed 0 bootstrap 95% CI; last column mean±sd over seeds)")
    comp = print_table(["V", "tokenizer", "contrast", "Δ tokens/word", "Δ boundary F1", "Δ t/w over seeds"],
                       comparisons)  # fmt: skip
    print("\nReading guide: ZWNJ removal deletes characters, so lower tokens/word under 'remove' is partly "
          "mechanical. Whether normalization explains the gain of a morphology-aware method is decided "
          "in 04_intrinsic_eval.py (normalization share).")  # fmt: skip
    gdir = out / exp_id("G0-summary", ds)
    gdir.mkdir(parents=True, exist_ok=True)
    (gdir / "table.txt").write_text(table + "\n\n" + comp + "\n", encoding="utf-8")
    (gdir / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(f"\nsaved {gdir}")
    return 0


def fertility_stat(units: list) -> float:
    """Ratio-of-sums fertility for bootstrap resamples."""
    f = fertility(units)
    return f if f is not None else 0.0


if __name__ == "__main__":
    raise SystemExit(main())
