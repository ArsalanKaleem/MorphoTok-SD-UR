"""Gate 5 report: apply PREREG.md §9 to the Kaggle language-model results.

Reads ``results/lm_kaggle/results_lm_<lang>.jsonl`` and writes ``report_lm_<lang>.md`` next
to it. Contrasts are paired by seed (tokenizer seed = LM seed); 95% t-interval over the 3
per-seed differences. Negative Δbpc = better language model.

    python scripts/15_lm_report.py --lang sd
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T95 = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776}
METRICS = [("test_bpc", "all test text"), ("test_bpc_heldout_lemma", "held-out-lemma words"),
           ("test_bpc_oov_form", "forms unseen in LM training"), ("test_bpc_seen_form", "seen forms")]  # fmt: skip
CONTRASTS = [("unigram_hard_trainonly", "unigram", True), ("bpe", "unigram", False)]


def ci(xs: list[float]) -> tuple[float, float, float]:
    """Mean and 95% t-interval."""
    m = statistics.fmean(xs)
    if len(xs) < 2:
        return m, float("nan"), float("nan")
    h = T95.get(len(xs), 1.96) * statistics.stdev(xs) / math.sqrt(len(xs))
    return m, m - h, m + h


def verdict(m: float, lo: float, hi: float) -> str:
    """PREREG §9 decision rule."""
    if hi < 0:
        return "**transfer** (better LM)"
    if lo > 0:
        return "**harm** (worse LM)"
    return "no detectable effect"


def main() -> int:
    """Write the report."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lang", required=True, choices=["sd", "ur"])
    ap.add_argument("--dir", type=Path, default=ROOT / "results" / "lm_kaggle")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    rows = [
        json.loads(ln)
        for ln in (a.dir / f"results_lm_{a.lang}.jsonl").read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    runs = {(r["tokenizer"], r["vocab"], r["seed"]): r for r in rows}  # a later line replaces an earlier one
    vocabs = sorted({k[1] for k in runs})
    toks = sorted({k[0] for k in runs})
    out = [f"# Gate 5 language-model results ({a.lang})", "",
           f"{len(runs)} runs. Bits per character (lower is better), mean ± sd over seeds.", "",
           "| tokenizer | V | test bpc | held-out-lemma bpc | unseen-form bpc | tokens/char | steps |",
           "|---|---|---|---|---|---|---|"]  # fmt: skip
    for v in vocabs:
        for t in toks:
            rs = [runs[(t, v, s)] for s in (0, 1, 2) if (t, v, s) in runs]
            if not rs:
                continue

            def ms(key: str, rs: list[dict] = rs) -> str:
                xs = [r[key] for r in rs if r[key] is not None]
                return f"{statistics.fmean(xs):.4f} ± {statistics.stdev(xs) if len(xs) > 1 else 0:.4f}"

            out.append(f"| {t} | {v} | {ms('test_bpc')} | {ms('test_bpc_heldout_lemma')} | {ms('test_bpc_oov_form')} "
                       f"| {statistics.fmean(r['tokens_per_char_test'] for r in rs):.3f} "
                       f"| {statistics.fmean(r['steps'] for r in rs):.0f} |")  # fmt: skip
    out += ["", "## Paired contrasts (Δbpc = system − reference; 95% t-interval over seeds)", "",
            "| contrast | V | text | Δbpc | 95% CI | verdict (§9 rule) |", "|---|---|---|---|---|---|"]  # fmt: skip
    for sys_, ref, primary in CONTRASTS:
        for v in vocabs:
            for key, label in METRICS:
                d = [runs[(sys_, v, s)][key] - runs[(ref, v, s)][key] for s in (0, 1, 2)
                     if (sys_, v, s) in runs and (ref, v, s) in runs
                     and runs[(sys_, v, s)][key] is not None and runs[(ref, v, s)][key] is not None]  # fmt: skip
                if not d:
                    continue
                m, lo, hi = ci(d)
                tag = " (primary)" if primary and key == "test_bpc" else ""
                out.append(f"| `{sys_} − {ref}`{tag} | {v} | {label} | {m:+.4f} | [{lo:+.4f}, {hi:+.4f}] | "
                           f"{verdict(m, lo, hi)} (n={len(d)}) |")  # fmt: skip
    text = "\n".join(out) + "\n"
    print(text)
    (a.dir / f"report_lm_{a.lang}.md").write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
