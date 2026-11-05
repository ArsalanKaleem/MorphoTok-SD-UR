"""Report for the POS study (``07_pos_tagging.py``): morphology vs spelling diagnostics.

For each budget and system: mean ± sd over seeds of accuracy on all test tokens,
unseen-lemma tokens, unseen-form tokens, and the perturbed tokens (clean / confusable /
random-noise). Robustness is reported as the *drop* from clean to perturbed on the same
tokens. Paired, seed-matched differences against a reference system get a t-interval
over seeds.

Key diagnostic (combined plan, C1 vs C2): for each system, the gain over the ``word``
baseline on **unseen lemmas** (morphological generalization) next to the gain in
**confusable-spelling accuracy** (orthographic robustness), with the random-noise control
alongside. Only the latest record per (system, budget, seed) is used; earlier smoke-test
records are superseded.
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

METRICS = (
    "acc_all",
    "acc_unseen_lemma",
    "acc_oov_form",
    "acc_pert_clean",
    "acc_pert_confusable",
    "acc_pert_noise",
)


def load(lang: str) -> dict[tuple[str, str], dict[int, dict]]:
    """(system, budget) -> seed -> metrics, latest record wins."""
    prefix = f"{lang.upper()}-POS-"
    out: dict[tuple[str, str], dict[int, dict]] = defaultdict(dict)
    for line in (ROOT / "runs" / "ledger.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if not r["experiment_id"].startswith(prefix) or r["status"] != "ok":
            continue
        rec = json.loads((ROOT / "runs" / r["path"]).read_text(encoding="utf-8"))
        job = rec["config_hash"] and rec.get("tokenizer", {}).get("name")
        budget = r["experiment_id"].rsplit("-B", 1)[1]
        m = rec["metrics"]
        m["drop_confusable"] = m["acc_pert_clean"] - m["acc_pert_confusable"]
        m["drop_noise"] = m["acc_pert_clean"] - m["acc_pert_noise"]
        out[(job, budget)][int(r["seed"])] = m
    return out


def fmt(agg: dict, signed: bool = False) -> str:
    """Mean [CI] or mean±sd."""
    if agg["mean"] is None:
        return "n/a"
    s = "+" if signed else ""
    if agg["ci_low"] is not None and signed:
        return f"{agg['mean']:{s}.3f} [{agg['ci_low']:{s}.3f},{agg['ci_high']:{s}.3f}]"
    return f"{agg['mean']:.3f}" + (f"±{agg['sd']:.3f}" if agg["sd"] is not None else "")


def table(headers: list[str], rows: list[list[str]]) -> str:
    """Markdown table."""
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def main() -> int:
    """Print and save the report."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lang", default="sd")
    a = ap.parse_args()
    data = load(a.lang)
    if not data:
        print("no POS runs found")
        return 1
    budgets = sorted({b for _, b in data}, key=float)
    systems = sorted({s for s, _ in data}, key=lambda s: (s.split(":")[0] != "word", s))
    parts = [
        f"# POS study report ({a.lang})\n",
        "Mean ± sd over seeds; paired deltas: mean [95% t-CI over seeds].\n",
    ]
    for b in budgets:
        rows = []
        for s in systems:
            seeds = data.get((s, b), {})
            if not seeds:
                continue
            row = [s, str(len(seeds))]
            row += [fmt(aggregate_seeds([m[k] for m in seeds.values()])) for k in
                    ("acc_all", "acc_unseen_lemma", "acc_oov_form", "drop_confusable", "drop_noise")]  # fmt: skip
            rows.append(row)
        parts.append(f"\n## Budget {b} (fraction of UD train sentences)\n")
        parts.append(
            table(
                ["system", "seeds", "all", "unseen lemma", "unseen form", "drop: confusable", "drop: noise"],
                rows,
            )
        )
        for ref in ("word", "sub:unigram", "gated:unigram", "gated:bpe"):
            base = data.get((ref, b))
            if not base:
                continue
            drows = []
            for s in systems:
                if s == ref or (s, b) not in data:
                    continue
                cur = data[(s, b)]
                common = sorted(set(base) & set(cur))
                if not common:
                    continue
                d = {k: aggregate_seeds([cur[i][k] - base[i][k] for i in common]) for k in
                     ("acc_all", "acc_unseen_lemma", "acc_pert_confusable", "acc_pert_noise")}  # fmt: skip
                drows.append([s, str(len(common))] + [fmt(d[k], signed=True) for k in d])
            parts.append(f"\n**Paired difference vs `{ref}` (budget {b})**\n")
            parts.append(
                table(["system", "pairs", "Δ all", "Δ unseen lemma", "Δ confusable", "Δ noise"], drows)
            )
    text = "\n".join(parts) + "\n"
    out = ROOT / "runs" / f"{a.lang.upper()}-POS-report.md"
    out.write_text(text, encoding="utf-8")
    print(text)
    print(f"saved {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
