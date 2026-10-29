"""Gate 5 *proxy*: token-bigram LM bits per character for every trained tokenizer.

For each model in the manifest written by ``03_train_tokenizers.py``: encode the train
split (seeded subsample, as in training) and the dev split, fit an add-k token-bigram
LM on train, and report dev **bits per stripped character** (comparable across
tokenizers, unlike per-token perplexity). This is a cheap CPU sanity proxy and **not** a
neural language-model result (see ``downstream/lm_small.py``).

Added beyond the required tree to give H7 a first, explicitly limited data point.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from morphtok.data.loaders import DataUnavailableError
from morphtok.downstream.lm_small import BigramLM
from morphtok.eval.stats import aggregate_seeds
from morphtok.experiments.results import finalise, new_record
from morphtok.experiments.runner import (
    SYNTHETIC_BANNER,
    build_analyzer,
    cli,
    exp_id,
    load_dataset,
    make_pipeline,
    mean_sd,
    print_table,
    train_lines_for_seed,
)
from morphtok.tokenizers.baselines import tokenizer_from_dict


def _args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--k", type=float, default=0.1, help="add-k smoothing constant")


def main() -> int:
    """Fit and score the bigram proxy for every model in the manifest."""
    args, run, out = cli(__doc__ or "", _args)
    try:
        ds = load_dataset(run)
    except DataUnavailableError as e:
        print(f"LM PROXY SKIPPED: {e}")
        return 2
    if ds.synthetic:
        print(SYNTHETIC_BANNER)
    manifest_path = out / exp_id("models", ds) / "manifest.json"
    if not manifest_path.exists():
        print(f"No manifest at {manifest_path}; run `make tokenizer` first.")
        return 2
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    analyzer = build_analyzer(ds)
    dev = ds.splits["dev"]
    results: dict[tuple[str, int], list[float | None]] = {}
    for m in manifest:
        name, vocab, seed = m["tokenizer"], int(m["vocab"]), int(m["seed"])
        pipe = make_pipeline(run["tokenizer_cfgs"][name], vocab, analyzer)
        pipe.tokenizer = tokenizer_from_dict(json.loads((out / m["path"]).read_text(encoding="utf-8")))
        rec = new_record(exp_id(f"LMPROXY-{name}-V{vocab}", ds), seed, {"run": run, "k": args.k},
                         ds.describe(), ds.synthetic, vocab, pipe.policy.describe(),
                         {"name": name, "model_run_id": m["run_id"]})  # fmt: skip
        try:
            train = train_lines_for_seed(ds, seed, float(run["train_fraction"]))
            enc_train = [[t for _, toks in pipe.encode_line(ln) for t in toks] for ln in train]
            dev_enc = [pipe.encode_line(ln) for ln in dev]
            n_chars = sum(pw.to_stripped[-1] for line in dev_enc for pw, _ in line)
            lm = BigramLM(k=args.k)
            lm.fit(enc_train)
            bpc = lm.bits_per_char([[t for _, toks in line for t in toks] for line in dev_enc], n_chars)
        except Exception as e:  # noqa: BLE001
            finalise(rec, out, "failed", e)
            results.setdefault((name, vocab), []).append(None)
            continue
        rec["metrics"] = {"bits_per_char": bpc, "n_dev_chars": n_chars, "proxy": "token-bigram add-k"}
        finalise(rec, out)
        results.setdefault((name, vocab), []).append(bpc)
    rows = [[str(v), n, mean_sd(vals, 4), f"{aggregate_seeds(vals)['n_ok']}/{len(vals)}"]
            for (n, v), vals in sorted(results.items(), key=lambda kv: (kv[0][1], kv[0][0]))]  # fmt: skip
    print("\nToken-bigram LM PROXY: dev bits per stripped character (lower is better; NOT a neural LM)")
    print_table(["V", "system", "bits/char", "ok"], rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
