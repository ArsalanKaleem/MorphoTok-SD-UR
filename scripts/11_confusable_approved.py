"""Re-score the spelling-robustness (confusable) test using only native-approved substitutions.

The confusable test replaces letters by a visually confusable code point
(``build_pos_tasks.SUBST``). A native reviewer judged spelling pairs in
``data/gold/<lang>_approved_variants.tsv`` (SAME) and in the review sheet (DIFFERENT /
UNSURE). A perturbed test token is **approved** unless its original form appears in a
reviewed pair, involving the substituted letters only, that was judged DIFFERENT or UNSURE
(e.g. Sindhi کي -> کی, where کی is a different, Urdu word).

Re-uses the per-token correctness bits stored in each POS run record; nothing is retrained.
Reports, per system and budget, the confusable and random-noise accuracy drops on (a) all
perturbed tokens and (b) approved perturbed tokens only, and the paired drop difference vs
``word`` (t-interval over seeds). Writes ``results/human_gold/confusable_<lang>.md``.

    python scripts/11_confusable_approved.py --lang sd
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_pos_tasks import SUBST  # noqa: E402

TCRIT = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776}


def t_ci(xs: list[float]) -> tuple[float, float, float]:
    """Mean and 95% t-interval."""
    m = statistics.fmean(xs)
    if len(xs) < 2:
        return m, m, m
    h = TCRIT.get(len(xs), 2.0) * statistics.stdev(xs) / len(xs) ** 0.5
    return m, m - h, m + h


def rejected_forms(lang: str) -> set[str]:
    """Original forms whose substitution a reviewer judged DIFFERENT or UNSURE."""
    sheet = ROOT / "data" / "audit" / "review" / f"{lang}_letter_variants.tsv"
    lines = sheet.read_text(encoding="utf-8-sig").splitlines()
    h = lines[0].split("\t")
    ix = {k: i for i, k in enumerate(h)}
    sub = SUBST[lang]
    out = set()
    for ln in lines[1:]:
        x = (ln.split("\t") + [""] * len(h))[: len(h)]
        a = x[ix["spelling_A (count)"]].rsplit(" (", 1)[0]
        b = x[ix["spelling_B (count)"]].rsplit(" (", 1)[0]
        if x[ix["decision"]].strip().upper() in ("DIFFERENT", "UNSURE"):
            if "".join(sub.get(c, c) for c in a) == b:  # the pair is exactly our substitution
                out.add(a)
    return out


def flat_tokens(path: Path) -> list[str]:
    """All test tokens in file order (aligned with the per-token bit strings)."""
    toks: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            toks += json.loads(line)["tokens"]
    return toks


def acc(bits: str, mask: list[bool]) -> float:
    """Accuracy over masked positions."""
    sel = [b for b, m in zip(bits, mask, strict=True) if m]
    return sum(c == "1" for c in sel) / len(sel)


def main() -> int:
    """Compute drops on all vs approved perturbed tokens."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lang", required=True, choices=["sd", "ur"])
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    bad = rejected_forms(a.lang)
    toks = flat_tokens(ROOT / "data" / "tasks" / f"{a.lang}_pos" / "test.jsonl")
    prefix = f"{a.lang.upper()}-POS-"
    rows_by_seed: dict[tuple[str, str], dict[int, dict]] = defaultdict(dict)
    n_all = n_ok = 0
    for d in sorted((ROOT / "runs").glob(prefix + "*")):
        for f in sorted(d.glob("*.json")):  # timestamped names: a later rerun replaces an earlier one
            rec = json.loads(f.read_text(encoding="utf-8"))
            if rec.get("status") != "ok" or "per_token" not in rec:
                continue
            pt = rec["per_token"]
            pert = [c == "1" for c in pt["perturbed_mask"]]
            assert len(pert) == len(toks), "token alignment mismatch"
            ok = [p and t not in bad for p, t in zip(pert, toks, strict=True)]
            n_all, n_ok = sum(pert), sum(ok)
            system, budget = d.name[len(prefix) :].rsplit("-B", 1)
            r = {}
            for name, mask in (("all", pert), ("approved", ok)):
                clean = acc(pt["test"], mask)
                r[f"conf_drop_{name}"] = clean - acc(pt["test_confusable"], mask)
                r[f"noise_drop_{name}"] = clean - acc(pt["test_randnoise"], mask)
            rows_by_seed[(system, budget)][int(rec["seed"])] = {"seed": int(rec["seed"]), **r}
    rows = {k: list(v.values()) for k, v in rows_by_seed.items()}
    out = [
        f"# Confusable test re-scored with native-approved substitutions ({a.lang})",
        "",
        f"Substitution: {SUBST[a.lang]}. Reviewer rejected (DIFFERENT/UNSURE) original forms: "
        f"{', '.join(sorted(bad)) or 'none'}.",
        f"Perturbed test tokens: {n_all}; approved: {n_ok} ({n_all - n_ok} removed).",
        "",
        "Drop = clean accuracy − perturbed accuracy on the same tokens (mean over seeds). Lower is more robust.",
        "",
        "| system | budget | confusable drop (all) | confusable drop (approved) | noise drop (approved) "
        "| Δ approved conf. drop vs word [95% t-CI] |",
        "|---|---|---|---|---|---|",
    ]  # fmt: skip
    budgets = sorted({b for _, b in rows}, key=float)
    for b in budgets:
        word = {r["seed"]: r for r in rows.get(("word", b), [])}
        for (s, bb), rs in sorted(rows.items()):
            if bb != b:
                continue
            m = {k: statistics.fmean(r[k] for r in rs) for k in rs[0] if k != "seed"}
            cell = ""
            if s != "word" and word:
                diffs = [
                    r["conf_drop_approved"] - word[r["seed"]]["conf_drop_approved"]
                    for r in rs
                    if r["seed"] in word
                ]
                mu, lo, hi = t_ci(diffs)
                cell = f"{mu:+.3f} [{lo:+.3f}, {hi:+.3f}] (n={len(diffs)})"
            out.append(f"| {s} | {b} | {m['conf_drop_all']:.3f} | {m['conf_drop_approved']:.3f} | "
                       f"{m['noise_drop_approved']:.3f} | {cell} |")  # fmt: skip
    text = "\n".join(out) + "\n"
    print(text)
    dest = ROOT / "results" / "human_gold"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"confusable_{a.lang}.md").write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
