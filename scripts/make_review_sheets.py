"""Generate native-speaker review sheets in ``data/audit/review/`` (local; not committed).

Sheets (UTF-8 with BOM so Excel shows Arabic script correctly; tab-separated):

1. ``<lang>_boundaries.tsv``: held-out (dev-lemma) word types for human morpheme
   boundaries. The ``segmentation`` column is pre-filled with the unsegmented word, and
   the reviewer inserts ``+`` between morphemes. Silver boundaries are deliberately NOT
   shown, to avoid anchoring. One corpus context is given when the word occurs.
2. ``<lang>_zwnj.tsv``: copy of the Gate 1 ZWNJ annotation sheet (label each occurrence).
3. ``<lang>_letter_variants.tsv``: pairs of spellings that differ only in yeh/kaf/heh
   code points (the most frequent spelling vs each variant seen at least twice), ordered
   by group frequency. The reviewer decides SAME word vs DIFFERENT word per pair.

Completed sheets are validated and imported by ``scripts/ingest_review.py``.
"""

from __future__ import annotations

import argparse
import random
import shutil
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "audit" / "review"
CORPUS = {
    "sd": ROOT / "data" / "processed" / "sd_wiki20231101_pilot66141.txt",
    "ur": ROOT / "data" / "processed" / "ur_wiki20231101_pilot853889.txt",
}
ZWNJ_SHEET = {
    "sd": ROOT / "runs" / "SD-G1-zwnj-audit" / "zwnj_annotation_sheet.tsv",
    "ur": ROOT / "runs" / "UR-G1-zwnj-audit" / "zwnj_annotation_sheet.tsv",
}
GROUPS = {
    "yeh": ("ي", "ی", "ى", "ے"),
    "kaf": ("ك", "ک", "ڪ"),
    "heh": ("ه", "ہ", "ھ", "ە"),
}
CP_NAME = {
    "ي": "Arabic yeh ي",
    "ی": "Farsi yeh ی",
    "ى": "alef maksura ى",
    "ے": "yeh barree ے",
    "ك": "Arabic kaf ك",
    "ک": "keheh ک",
    "ڪ": "swash kaf ڪ",
    "ه": "heh ه",
    "ہ": "heh goal ہ",
    "ھ": "heh doachashmee ھ",
    "ە": "ae ە",
}


def write_tsv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    """Write a BOM-prefixed UTF-8 TSV (tabs/newlines inside cells replaced by spaces)."""
    clean = [[c.replace("\t", " ").replace("\n", " ") for c in r] for r in rows]
    text = "\n".join(["\t".join(header)] + ["\t".join(r) for r in clean]) + "\n"
    path.write_text(text, encoding="utf-8-sig", newline="\n")


def boundary_sheet(lang: str, n: int, seed: int) -> int:
    """Sample held-out (dev) silver word types and attach one corpus context each."""
    silver = ROOT / "data" / "gold" / f"{lang}_silver.tsv"
    words = []
    for line in silver.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line:
            continue
        w, _b, _src, split = line.split("\t")
        if split == "dev" and len(w) >= 2:
            words.append(w)
    rng = random.Random(seed)
    sample = sorted(rng.sample(sorted(words), min(n, len(words))))
    want = set(sample)
    ctx: dict[str, str] = {}
    with CORPUS[lang].open(encoding="utf-8") as fh:
        for line in fh:
            toks = line.split()
            for i, t in enumerate(toks):
                if t in want and t not in ctx:
                    ctx[t] = " ".join(toks[max(0, i - 6) : i + 7])
            if len(ctx) == len(want):
                break
    rows = [[f"{lang}-B{i:03d}", w, w, "", ctx.get(w, ""), ""] for i, w in enumerate(sample, 1)]
    write_tsv(
        OUT / f"{lang}_boundaries.tsv", ["item_id", "word", "segmentation", "status", "context", "note"], rows
    )
    return len(rows)


def variant_sheet(lang: str, n: int) -> int:
    """Most frequent word groups whose spellings differ only in one yeh/kaf/heh code point."""
    counts: Counter[str] = Counter()
    with CORPUS[lang].open(encoding="utf-8") as fh:
        for line in fh:
            counts.update(line.split())
    canon = {m: g[0] for g in GROUPS.values() for m in g}
    folded: dict[str, list[str]] = {}
    for w in counts:
        if any(c in canon for c in w):
            folded.setdefault("".join(canon.get(c, c) for c in w), []).append(w)
    groups = [sorted(v, key=lambda x: (-counts[x], x)) for v in folded.values() if len(v) > 1]
    groups.sort(key=lambda g: -sum(counts[w] for w in g))
    rows = []
    for g in groups:
        top = g[0]
        for other in g[1:]:
            if counts[other] < 2:
                continue  # hapax variants are mostly typos; keep the sheet focused
            diff = [(a, b) for a, b in zip(top, other, strict=True) if a != b]
            letters = "; ".join(f"{CP_NAME.get(a, a)} vs {CP_NAME.get(b, b)}" for a, b in diff)
            rows.append([f"{lang}-V{len(rows) + 1:03d}", f"{top} ({counts[top]})", f"{other} ({counts[other]})",
                         letters, "", ""])  # fmt: skip
            if len(rows) >= n:
                break
        if len(rows) >= n:
            break
    write_tsv(
        OUT / f"{lang}_letter_variants.tsv",
        ["pair_id", "spelling_A (count)", "spelling_B (count)", "letters that differ", "decision", "note"],
        rows,
    )
    return len(rows)


def zwnj_sheet(lang: str) -> int:
    """Copy the Gate 1 sheet (re-encoded with BOM for spreadsheet apps)."""
    src = ZWNJ_SHEET[lang]
    text = src.read_text(encoding="utf-8-sig")
    (OUT / f"{lang}_zwnj.tsv").write_text(text, encoding="utf-8-sig", newline="\n")
    return len(text.splitlines()) - 1


def main() -> int:
    """Write every sheet and print where they are."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-boundaries", type=int, default=300)
    ap.add_argument("--n-variants", type=int, default=150)
    ap.add_argument("--seed", type=int, default=20261030)
    ap.add_argument(
        "--force", action="store_true", help="overwrite existing sheets (may destroy your answers)"
    )
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if any(OUT.glob("*.tsv")) and not a.force:
        print(f"Sheets already exist in {OUT}; refusing to overwrite (use --force).")
        return 1
    for lang in ("sd", "ur"):
        nb = boundary_sheet(lang, a.n_boundaries, a.seed)
        nz = zwnj_sheet(lang)
        nv = variant_sheet(lang, a.n_variants)
        print(f"{lang}: boundaries={nb} zwnj={nz} letter_variants={nv}")
    shutil.copy(ROOT / "audit" / "REVIEWING.md", OUT / "REVIEWING.md")
    print(f"written to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
