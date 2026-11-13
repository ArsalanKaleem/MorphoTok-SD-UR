"""Draw the README result figures from the files in results/ (PNG, written to docs/assets/).

    python scripts/17_readme_figures.py      (needs matplotlib: pip install matplotlib)

Every number is read from results/ or copied from the findings document named next to it.
"""

from __future__ import annotations

import json
import math
import statistics as st
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets"
T95 = 4.302652729911275  # t(0.975, df = 2)

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.size": 8.5,
        "axes.titlesize": 9,
        "axes.labelsize": 8.5,
        "legend.fontsize": 7.5,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
    }
)
C_SD, C_UR, C_NAT = "#2f5fa7", "#c0503a", "#3a8a5c"


def ci(xs: list[float]) -> tuple[float, float, float]:
    """Mean and 95% t-interval over three seeds."""
    m = st.fmean(xs)
    h = T95 * st.stdev(xs) / math.sqrt(len(xs))
    return m, m - h, m + h


def jsonl(path: Path) -> list[dict]:
    """Records of a JSON-lines file."""
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


# ---------------------------------------------------------------- Figure: tokenizer gains
def fig_tokenizer_gain() -> None:
    """Tokenizer gain on held-out lemmas (pilot test, full corpus, native gold)."""
    rows = []  # (group, label, mean, lo, hi, colour)
    # Pilot corpora, silver test, prereg-v1: results/final_test/decision.md
    for lang, v, m, lo, hi in (
        ("sd", 2000, 0.0301, 0.0203, 0.0398),
        ("sd", 4000, 0.0331, 0.0167, 0.0496),
        ("ur", 2000, 0.0064, 0.0043, 0.0084),
        ("ur", 4000, 0.0115, 0.0079, 0.0150),
    ):
        rows.append(
            (
                "Pilot corpora, silver test (preregistered)",
                f"{lang.upper()} V={v}",
                m,
                lo,
                hi,
                C_SD if lang == "sd" else C_UR,
            )
        )
    for lang in ("sd", "ur"):
        s = json.loads((ROOT / f"results/scale_full/summary_{lang}.json").read_text(encoding="utf-8"))
        for r in s["rows"]:
            if r["gold"] == "dev":
                rows.append(
                    (
                        "Full corpora, silver dev (preregistered)",
                        f"{lang.upper()} V={r['vocab']}",
                        r["mean"],
                        r["ci"][0],
                        r["ci"][1],
                        C_SD if lang == "sd" else C_UR,
                    )
                )
    # Native Sindhi gold, 267 dev words: docs/findings_human_review.md (pilot) and summary_sd.json (full)
    rows.append(("Native Sindhi gold, 267 dev words", "pilot V=2000", 0.001, -0.006, 0.008, C_NAT))
    rows.append(("Native Sindhi gold, 267 dev words", "pilot V=4000", 0.022, 0.002, 0.043, C_NAT))
    s = json.loads((ROOT / "results/scale_full/summary_sd.json").read_text(encoding="utf-8"))
    for r in s["rows"]:
        if r["gold"] == "human":
            rows.append(
                (
                    "Native Sindhi gold, 267 dev words",
                    f"full V={r['vocab']}",
                    r["mean"],
                    r["ci"][0],
                    r["ci"][1],
                    C_NAT,
                )
            )

    fig, ax = plt.subplots(figsize=(6.3, 4.1))
    y, ticks, labels, groups = 0, [], [], []
    last = None
    for g, lab, m, lo, hi, col in rows:
        if g != last:
            y -= 0.9 if last else 0
            groups.append((y, g))
            y -= 1
            last = g
        ax.errorbar(m, y, xerr=[[m - lo], [hi - m]], fmt="o", color=col, ms=4, capsize=2.5, lw=1.2)
        ticks.append(y)
        labels.append(lab)
        y -= 1
    for gy, g in groups:
        ax.text(-0.0105, gy, g, fontsize=8, fontweight="bold", va="center", ha="left")
    ax.axvline(0, color="0.3", lw=0.8)
    ax.axvline(0.010, color="0.5", lw=0.8, ls="--")
    ax.text(
        0.0106, groups[0][0] + 1.15, "preregistered threshold +0.010", fontsize=6.5, color="0.35", va="center"
    )
    ax.set_yticks(ticks, labels)
    ax.set_xlim(-0.011, 0.077)
    ax.set_ylim(y + 0.3, groups[0][0] + 1.6)
    ax.set_xlabel(
        r"$\Delta$ boundary F1 on held-out lemmas (supervised $-$ plain Unigram); mean, 95% CI over 3 seeds"
    )
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    fig.tight_layout()
    fig.savefig(OUT / "fig_tokenizer_gain.png", dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------- Figure: language-model deltas
def lm_deltas(path: Path, key: str) -> dict[int, tuple[float, float, float]]:
    """Paired supervised minus plain Unigram bpc per vocabulary size."""
    rs = {(r["tokenizer"], r["vocab"], r["seed"]): r for r in jsonl(path)}
    out = {}
    for v in sorted({k[1] for k in rs}):
        d = [rs[("unigram_hard_trainonly", v, s)][key] - rs[("unigram", v, s)][key] for s in (0, 1, 2)]
        out[v] = ci(d)
    return out


def fig_lm() -> None:
    """Language-model bpc differences, pilot and full corpora."""
    fig, axes = plt.subplots(1, 2, figsize=(6.3, 2.6), sharey=False)
    for ax, (study, folder) in zip(
        axes,
        (("Pilot corpora (5k lines)", "lm_kaggle"), ("Full corpora (53k / 150k lines)", "lm_full_kaggle")),
        strict=True,
    ):
        ticks, labels, y = [], [], 0
        for lang, col in (("sd", C_SD), ("ur", C_UR)):
            p = ROOT / "results" / folder / f"results_lm_{lang}.jsonl"
            allt, held = lm_deltas(p, "test_bpc"), lm_deltas(p, "test_bpc_heldout_lemma")
            for v in allt:
                m, lo, hi = allt[v]
                ax.errorbar(
                    m,
                    y,
                    xerr=[[m - lo], [hi - m]],
                    fmt="o",
                    color=col,
                    ms=4,
                    capsize=2.5,
                    lw=1.2,
                    label="all test text" if (lang, v) == ("sd", min(allt)) else None,
                )
                hm, hlo, hhi = held[v]
                ax.errorbar(
                    hm,
                    y - 0.32,
                    xerr=[[hm - hlo], [hhi - hm]],
                    fmt="o",
                    mfc="white",
                    color=col,
                    ms=3.5,
                    capsize=2,
                    lw=0.9,
                    alpha=0.9,
                    label="held-out-lemma words" if (lang, v) == ("sd", min(allt)) else None,
                )
                ticks.append(y - 0.16)
                labels.append(f"{lang.upper()} V={v}")
                y -= 1.2
        ax.axvline(0, color="0.3", lw=0.8)
        ax.set_yticks(ticks, labels)
        ax.set_title(study)
        ax.set_xlabel(r"$\Delta$ bits per character (lower = better LM)")
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", length=0)
    axes[1].set_xlim(-0.23, 0.23)
    axes[0].set_xlim(-0.23, 0.23)
    from matplotlib.lines import Line2D

    h = [
        Line2D([], [], marker="o", ls="", color="0.25", ms=4),
        Line2D([], [], marker="o", ls="", mfc="white", color="0.25", ms=3.5),
    ]
    fig.legend(
        h,
        ["all test text", "words of held-out lemmas"],
        loc="lower center",
        ncol=2,
        frameon=False,
        bbox_to_anchor=(0.5, -0.02),
    )
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(OUT / "fig_lm_deltas.png", dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------- Figure: LM training curves
def fig_curves() -> None:
    """Dev bpc training curves, pilot vs full corpus."""
    fig, axes = plt.subplots(1, 2, figsize=(6.3, 2.3), sharey=False)
    for ax, (lang, col) in zip(axes, (("sd", C_SD), ("ur", C_UR)), strict=True):
        for folder, ls, _name in (
            ("lm_kaggle", "--", "pilot corpus"),
            ("lm_full_kaggle", "-", "full corpus"),
        ):
            for r in jsonl(ROOT / "results" / folder / f"results_lm_{lang}.jsonl"):
                if (
                    r["vocab"] == 4000
                    and r["seed"] == 0
                    and r["tokenizer"] in ("unigram", "unigram_hard_trainonly")
                ):
                    h = r["history"]
                    lw = 1.3 if r["tokenizer"] == "unigram" else 0.9
                    alpha = 1.0 if r["tokenizer"] == "unigram" else 0.55
                    ax.plot(
                        [e[0] for e in h],
                        [e[1] for e in h],
                        ls=ls,
                        color=col,
                        lw=lw,
                        alpha=alpha,
                    )
        ax.set_title({"sd": "Sindhi", "ur": "Urdu"}[lang] + ", V=4000, seed 0")
        ax.set_xlabel("training step")
        ax.set_ylabel("dev bits per character")
        ax.set_ylim(1.5, 3.2)
    from matplotlib.lines import Line2D

    h = [
        Line2D([], [], color="0.2", ls="--", lw=1.3),
        Line2D([], [], color="0.2", ls="-", lw=1.3),
        Line2D([], [], color="0.2", lw=1.3),
        Line2D([], [], color="0.2", lw=0.9, alpha=0.55),
    ]
    fig.legend(
        h,
        ["pilot corpus (5k lines)", "full corpus", "plain Unigram (dark)", "train-only supervised (light)"],
        loc="lower center",
        ncol=4,
        frameon=False,
        fontsize=7,
        bbox_to_anchor=(0.5, -0.02),
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(OUT / "fig_lm_curves.png", dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------- Figure: ZWNJ frequency
def fig_zwnj() -> None:
    """ZWNJ frequency in real text against normative annotation."""
    # docs/findings_pilot.md section 1 (ZWNJ per 100k words)
    data = [
        ("Sindhi UD-Isra (news)", 1.1, C_SD),
        ("Sindhi Wikipedia", 2.9, C_SD),
        ("Urdu UD-UDTB (news)", 0.7, C_UR),
        ("Urdu Wikipedia", 10.1, C_UR),
        ("Urdu, normative annotation\n(Zia et al., 2018)", 5779, "0.45"),
    ]
    fig, ax = plt.subplots(figsize=(6.3, 1.9))
    ys = list(range(len(data)))[::-1]
    for y, (_name, v, col) in zip(ys, data, strict=True):
        ax.barh(y, v, color=col, height=0.6)
        ax.text(v * 1.15, y, f"{v:,.1f}" if v < 100 else f"{v:,.0f}", va="center", fontsize=7.5)
    ax.set_yticks(ys, [d[0] for d in data])
    ax.set_xscale("log")
    ax.set_xlim(0.4, 30000)
    ax.set_xlabel("ZWNJ characters per 100,000 words (log scale)")
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    fig.tight_layout()
    fig.savefig(OUT / "fig_zwnj.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    fig_tokenizer_gain()
    fig_lm()
    fig_curves()
    fig_zwnj()
    print("wrote", sorted(p.name for p in OUT.glob("fig_*.png")))
