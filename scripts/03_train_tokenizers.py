"""Train every configured tokenizer x vocabulary size x seed and save the models.

Models go to ``runs/<prefix>models/<tokenizer>/V<size>/seed<seed>.json`` with a
``manifest.json`` consumed by ``04_intrinsic_eval.py``. Each training run gets a full
provenance record, including hard-constraint fallbacks, constraint conflicts and
whether the vocabulary size was matched.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from morphtok.data.loaders import DataUnavailableError
from morphtok.experiments.results import finalise, new_record
from morphtok.experiments.runner import (
    SYNTHETIC_BANNER,
    build_analyzer,
    cli,
    exp_id,
    load_dataset,
    make_pipeline,
    print_table,
    train_lines_for_seed,
)


def main() -> int:
    """Train all conditions; failures are recorded and listed, never skipped silently."""
    _, run, out = cli(__doc__ or "")
    try:
        ds = load_dataset(run)
    except DataUnavailableError as e:
        print(f"TRAINING SKIPPED: {e}")
        return 2
    if ds.synthetic:
        print(SYNTHETIC_BANNER)
    analyzer = build_analyzer(ds)
    model_root = out / exp_id("models", ds)
    manifest: list[dict[str, object]] = []
    rows = []
    for name in run["tokenizers"]:
        tok_cfg = run["tokenizer_cfgs"][name]
        if tok_cfg.get("requires_analyzer") and not analyzer.is_configured:
            print(f"skip {name}: requires an analyzer and none is configured")
            rec = new_record(exp_id(f"TRAIN-{name}", ds), None, run, ds.describe(), ds.synthetic)
            rec["skipped_steps"].append("no analyzer configured")
            finalise(rec, out, "skipped")
            continue
        for vocab in run["vocab_sizes"]:
            for seed in run["seeds"]:
                pipe = make_pipeline(tok_cfg, vocab, analyzer)
                rec = new_record(exp_id(f"TRAIN-{name}-V{vocab}", ds), seed, {"run": run, "tok": tok_cfg},
                                 ds.describe(), ds.synthetic, vocab, pipe.policy.describe(),
                                 {"name": name, "version": pipe.tokenizer.version})  # fmt: skip
                try:
                    pipe.train(train_lines_for_seed(ds, seed, float(run["train_fraction"])))
                except Exception as e:  # noqa: BLE001
                    finalise(rec, out, "failed", e)
                    rows.append([name, str(vocab), str(seed), "FAILED", "", ""])
                    continue
                path = model_root / name / f"V{vocab}" / f"seed{seed}.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                pipe.tokenizer.save(str(path))
                log = getattr(pipe.tokenizer, "training_log", None)
                rec["metrics"] = {
                    "realised_vocab": pipe.tokenizer.vocab_size,
                    "hard_fallbacks": log.hard_fallbacks if log else None,
                    "zero_count_pieces_final": log.zero_count_pieces_final if log else None,
                    "constraint_conflicts": pipe.stats.get("constraint_conflicts", 0),
                    "em_rounds": log.rounds if log else None,
                }
                rec["warnings"] += (log.warnings if log else []) + getattr(pipe.tokenizer, "warnings", [])
                if name != "char" and pipe.tokenizer.vocab_size != vocab:
                    rec["warnings"].append(f"vocab NOT matched: {pipe.tokenizer.vocab_size} != {vocab}")
                finalise(rec, out)
                manifest.append({"tokenizer": name, "vocab": vocab, "seed": seed,
                                 "path": path.relative_to(out).as_posix(), "run_id": rec["run_id"]})  # fmt: skip
                rows.append([name, str(vocab), str(seed), str(pipe.tokenizer.vocab_size),
                             str(rec["metrics"]["hard_fallbacks"]), str(rec["metrics"]["constraint_conflicts"])])  # fmt: skip
    model_root.mkdir(parents=True, exist_ok=True)
    (model_root / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print_table(["tokenizer", "V", "seed", "realised V", "hard fallbacks", "constraint conflicts"], rows)
    print(f"\nmanifest: {model_root / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
