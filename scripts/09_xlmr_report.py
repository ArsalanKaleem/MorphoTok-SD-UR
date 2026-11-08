"""Report for the XLM-R fusion runs (``scripts/xlmr_fusion.py`` on a Kaggle T4).

Reads ``results/xlmr_kaggle/results_<lang>.jsonl`` and prints, per budget: mean ± sd over
seeds of accuracy on all tokens, unseen-lemma tokens, unseen-form tokens, and the drops
on perturbed tokens (confusable substitution; random-letter control). It also prints
paired, seed-matched differences ``concat − base``, ``gated − base`` and ``gated − concat``
with a 95% t-interval over seeds (n = 3, so intervals are wide).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from morphtok.eval.stats import aggregate_seeds  # noqa: E402


def fmt(agg: dict, signed: bool = False) -> str:
    """mean±sd, or signed mean [t-CI]."""
    if agg["mean"] is None:
        return "n/a"
    if signed:
        if agg["ci_low"] is None:
            return f"{agg['mean']:+.3f}"
        return f"{agg['mean']:+.3f} [{agg['ci_low']:+.3f}, {agg['ci_high']:+.3f}]"
    return f"{agg['mean']:.3f}" + (f"±{agg['sd']:.3f}" if agg["sd"] is not None else "")


def table(headers: list[str], rows: list[list[str]]) -> str:
    """Markdown table."""
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    return "\n".join(lines + ["| " + " | ".join(r) + " |" for r in rows])


def main() -> int:
    """Print and save the report."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lang", default="sd")
    ap.add_argument("--dir", default=str(ROOT / "results" / "xlmr_kaggle"))
    a = ap.parse_args()
    rows = [
        json.loads(x)
        for x in (Path(a.dir) / f"results_{a.lang}.jsonl").read_text(encoding="utf-8").splitlines()
        if x
    ]
    data: dict[tuple[str, str], dict[int, dict]] = defaultdict(dict)
    for r in rows:
        r["drop_confusable"] = r["acc_pert_clean"] - r["acc_pert_confusable"]
        r["drop_noise"] = r["acc_pert_clean"] - r["acc_pert_noise"]
        data[(r["kind"], r["budget"])][int(r["seed"])] = r
    parts = [f"# XLM-R fusion report ({a.lang})\n",
             "XLM-R base fine-tuned on a Kaggle T4; mean ± sd over 3 seeds; paired deltas: mean [95% t-CI].\n"]  # fmt: skip
    for b in sorted({b for _, b in data}, key=float):
        out = []
        for k in ("base", "concat", "gated"):
            seeds = data.get((k, b), {})
            out.append([k, str(len(seeds))] + [fmt(aggregate_seeds([m[x] for m in seeds.values()])) for x in
                       ("acc_all", "acc_unseen_lemma", "acc_oov_form", "drop_confusable", "drop_noise")])  # fmt: skip
        parts += [f"\n## Budget {b}\n", table(["system", "seeds", "all", "unseen lemma", "unseen form",
                                              "drop: confusable", "drop: noise"], out)]  # fmt: skip
        drows = []
        for x, y in (("concat", "base"), ("gated", "base"), ("gated", "concat")):
            common = sorted(set(data[(x, b)]) & set(data[(y, b)]))
            d = {m: aggregate_seeds([data[(x, b)][s][m] - data[(y, b)][s][m] for s in common]) for m in
                 ("acc_all", "acc_unseen_lemma", "acc_pert_confusable", "acc_pert_noise")}  # fmt: skip
            drows.append([f"{x} − {y}", str(len(common))] + [fmt(d[m], signed=True) for m in d])
        parts += ["\n**Paired differences**\n", table(["contrast", "pairs", "Δ all", "Δ unseen lemma",
                                                        "Δ confusable", "Δ noise"], drows)]  # fmt: skip
    text = "\n".join(parts) + "\n"
    out_path = Path(a.dir) / f"report_{a.lang}.md"
    out_path.write_text(text, encoding="utf-8")
    print(text)
    print(f"saved {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
