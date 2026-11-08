"""Apply the frozen preregistration (prereg-v1, PREREG.md §4) to the one-time test evaluation.

Reads ``runs/<LANG>-EVAL-summary-test/comparisons.json`` (written by
``04_intrinsic_eval.py --split test --final``) and writes ``results/final_test/`` (metric-only):
the summary tables, the comparisons, and ``decision.md`` with the preregistered verdicts.

Primary contrast: unigram_hard_trainonly − unigram, V ∈ {2000, 4000}, both languages.
Pass = mean ΔF1 ≥ +0.010 and 95% t-interval over seeds excludes 0, and Δ tokens/word ≤ +5%.
Bonferroni (4 tests): 98.75% t-interval over seeds excludes 0.
"""

from __future__ import annotations

import json
import math
import shutil
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIN_GAIN, MAX_FERT = 0.010, 0.05
PRIMARY = "unigram_hard_trainonly_minus_unigram"
SECONDARY = ["unigram_soft_trainonly_minus_unigram", "unigram_soft_minus_unigram_hard",
             "bpe_minus_unigram", "unigram_zwnj_norm_minus_unigram"]  # fmt: skip


def t_df2(p: float) -> float:
    """Student t quantile for 2 degrees of freedom (closed form)."""
    return (2 * p - 1) / math.sqrt(2 * p * (1 - p))


def interval(deltas: list[float], level: float) -> tuple[float, float, float]:
    """Mean and two-sided t-interval over seeds (n = 3)."""
    assert len(deltas) == 3, "the preregistration fixes 3 seeds"
    m = statistics.fmean(deltas)
    h = t_df2(1 - (1 - level) / 2) * statistics.stdev(deltas) / math.sqrt(3)
    return m, m - h, m + h


def base_fertility(tables: str, v: int) -> float:
    """Mean tokens/word of `unigram` at vocabulary ``v`` from the summary table."""
    for line in tables.splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) > 6 and cells[0] == str(v) and cells[1] == "unigram":
            return float(cells[6].split("±")[0])
    raise ValueError(f"no unigram row for V={v}")


def main() -> int:
    """Write the decision report."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    dest = ROOT / "results" / "final_test"
    dest.mkdir(parents=True, exist_ok=True)
    out = ["# Final test evaluation under prereg-v1", "",
           "Evaluated once on the frozen commit with `04_intrinsic_eval.py --split test --final`. "
           "Test gold is **silver** (lemma-derived; on Sindhi dev it had P = 0.55 vs native gold). "
           "3 seeds, already-trained pilot models.", "",
           "## Primary contrast: `unigram_hard_trainonly − unigram`", "",
           "| lang | V | mean ΔF1 | 95% t-CI | 98.75% t-CI (Bonferroni) | Δ tok/word (rel.) | verdict |",
           "|---|---|---|---|---|---|---|"]  # fmt: skip
    sec = ["", "## Secondary contrasts (reported, not decisive)", "",
           "| lang | V | contrast | mean ΔF1 [95% t-CI] |", "|---|---|---|---|"]  # fmt: skip
    for lang in ("SD", "UR"):
        src = ROOT / "runs" / f"{lang}-EVAL-summary-test"
        if not (src / "comparisons.json").exists():
            print(f"missing {src}; run the test evaluation first")
            return 2
        shutil.copy(src / "tables.txt", dest / f"tables_{lang.lower()}.txt")
        shutil.copy(src / "comparisons.json", dest / f"comparisons_{lang.lower()}.json")
        comps = json.loads((src / "comparisons.json").read_text(encoding="utf-8"))["comparisons"]
        tables = (src / "tables.txt").read_text(encoding="utf-8")
        for v in (2000, 4000):
            c = comps[f"{PRIMARY}_V{v}"]
            f1 = [r["delta"] for r in c["f1"]]
            m, lo, hi = interval(f1, 0.95)
            _, blo, bhi = interval(f1, 0.9875)
            fert = c["fert_over_seeds"]["mean"] / base_fertility(tables, v)
            ok = m >= MIN_GAIN and lo > 0 and fert <= MAX_FERT
            verdict = ("**PASS**" if ok else "**FAIL**") + (
                " (survives Bonferroni)" if ok and blo > 0 else ""
            )
            out.append(f"| {lang.lower()} | {v} | {m:+.4f} | [{lo:+.4f}, {hi:+.4f}] | [{blo:+.4f}, {bhi:+.4f}] "
                       f"| {fert:+.2%} | {verdict} |")  # fmt: skip
            for name in SECONDARY:
                k = f"{name}_V{v}"
                if k in comps:
                    sm, slo, shi = interval([r["delta"] for r in comps[k]["f1"]], 0.95)
                    label = name.replace("_minus_", " − ")
                    sec.append(f"| {lang.lower()} | {v} | `{label}` | {sm:+.4f} [{slo:+.4f}, {shi:+.4f}] |")
    text = "\n".join(out + sec) + "\n"
    print(text)
    (dest / "decision.md").write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
