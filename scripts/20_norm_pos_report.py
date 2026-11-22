"""Report for the normalization x POS study (PREREG.md section 12): applies the decision rules.

    python scripts/20_norm_pos_report.py --dataset sipos     (primary)
    python scripts/20_norm_pos_report.py --dataset ud_sd     (replication, secondary)

Reads ``results/norm_pos/runs_<dataset>.jsonl`` (written by ``scripts/19_norm_pos.py``; a later
line for the same normalizer, system and seed replaces an earlier one) and writes
``results/norm_pos/report_<dataset>.md``.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T95 = 4.302652729911275  # t(0.975, df = 2): three seed-paired differences
NORMS = ("none", "freq", "keyboard")
LABEL = {"none": "none", "freq": "0.1.0 rules", "keyboard": "0.2.0 keyboard"}


def ci(xs: list[float]) -> tuple[float, float, float]:
    """Mean and 95% t-interval."""
    m = st.fmean(xs)
    h = T95 * st.stdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else float("nan")
    return m, m - h, m + h


def main() -> int:
    """Write the report."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", required=True, choices=["sipos", "ud_sd"])
    a = ap.parse_args()
    src = ROOT / "results" / "norm_pos" / f"runs_{a.dataset}.jsonl"
    runs = {}
    for ln in src.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            r = json.loads(ln)
            runs[(r["normalizer"], r["system"], r["seed"])] = r
    systems = [s for s in ("word", "char") if any(k[1] == s for k in runs)]
    seeds = sorted({k[2] for k in runs})
    title = "SiPOS (primary)" if a.dataset == "sipos" else "UD Sindhi-Isra (replication, secondary)"
    out = [f"# Normalization x POS tagging: {title}", "",
           f"{len(runs)} runs; seeds {seeds}. Accuracy on the test split (mean over seeds). "
           "`keyboard` = the test typed as on an Urdu keyboard; `noise` = one random letter changed in "
           "the same tokens; `pert` = only the altered tokens.", "",
           "| tagger | normalizer | clean | keyboard | noise | clean (pert) | keyboard (pert) | restored |",
           "|---|---|---|---|---|---|---|---|"]  # fmt: skip
    for s in systems:
        for n in NORMS:
            rs = [runs[(n, s, k)] for k in seeds if (n, s, k) in runs]
            if not rs:
                continue

            def mean(key: str, rs: list[dict] = rs) -> str:
                return f"{st.fmean(r[key] for r in rs):.4f}"

            out.append(f"| {s} | {LABEL[n]} | {mean('acc_clean')} | {mean('acc_keyboard')} | {mean('acc_kbnoise')} "
                       f"| {mean('acc_clean_pert')} | {mean('acc_keyboard_pert')} | {mean('restored_pert')} |")  # fmt: skip

    out += ["", "## Paired contrasts (mean difference, 95% t-interval over seeds)", "",
            "| tagger | contrast | test | Δ accuracy | 95% CI | verdict |", "|---|---|---|---|---|---|"]  # fmt: skip
    verdicts = {}
    for s in systems:
        for sys_, ref in (("keyboard", "none"), ("freq", "none"), ("keyboard", "freq")):
            for key, label in (
                ("acc_keyboard", "keyboard-typed"),
                ("acc_clean", "clean"),
                ("acc_kbnoise", "noise control"),
            ):
                d = [runs[(sys_, s, k)][key] - runs[(ref, s, k)][key] for k in seeds
                     if (sys_, s, k) in runs and (ref, s, k) in runs]  # fmt: skip
                if len(d) < 2:
                    continue
                m, lo, hi = ci(d)
                verdict = ""
                if a.dataset == "sipos" and s == "word" and (sys_, ref) == ("keyboard", "none"):
                    if key == "acc_keyboard":
                        verdict = "**helps** (H9a)" if (m >= 0.05 and lo > 0) else "**does not meet H9a**"
                        verdicts["H9a"] = verdict
                    elif key == "acc_clean":
                        verdict = "**harm** (H9b)" if (m < -0.002 and hi < 0) else "**no harm** (H9b)"
                        verdicts["H9b"] = verdict
                elif lo > 0 or hi < 0:
                    verdict = "interval excludes 0"
                out.append(
                    f"| {s} | {LABEL[sys_]} − {LABEL[ref]} | {label} | {m:+.4f} | [{lo:+.4f}, {hi:+.4f}] | {verdict} |"
                )

    out += ["", "## Recovery fraction", "",
            "(acc_keyboard(N) − acc_keyboard(none)) / (acc_clean(none) − acc_keyboard(none)), mean over seeds.", "",
            "| tagger | 0.1.0 rules | 0.2.0 keyboard |", "|---|---|---|"]  # fmt: skip
    for s in systems:
        cells = []
        for n in ("freq", "keyboard"):
            fr = []
            for k in seeds:
                if ("none", s, k) in runs and (n, s, k) in runs:
                    base = runs[("none", s, k)]
                    gap = base["acc_clean"] - base["acc_keyboard"]
                    fr.append(
                        (runs[(n, s, k)]["acc_keyboard"] - base["acc_keyboard"]) / gap
                        if gap
                        else float("nan")
                    )
            cells.append(f"{st.fmean(fr):.3f}" if fr else "n/a")
        out.append(f"| {s} | {cells[0]} | {cells[1]} |")
    if verdicts:
        out += ["", "## Preregistered verdicts (SiPOS, word tagger)", ""] + [
            f"* {k}: {v}" for k, v in verdicts.items()
        ]
    text = "\n".join(out) + "\n"
    print(text)
    (src.parent / f"report_{a.dataset}.md").write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
