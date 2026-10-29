"""Build lemma-derived SILVER boundary data and held-out paradigms for one language.

Inputs (``data/raw/``, provenance in ``data/raw/SOURCE.md``):
  sd: UD_Sindhi-Isra (train/dev/test CoNLL-U; manual lemmas; CC BY-SA 4.0)
  ur: UD_Urdu-UDTB (CoNLL-U; CC BY-NC-SA 4.0) + UniMorph urd (CC BY-SA 3.0)

Outputs:
  data/gold/<lang>_silver.tsv              word, majority boundaries, source, split (by lemma)
  data/gold/<lang>_paradigms_heldout.json  lemma -> {split, forms}, dev/test lemmas only
  data/gold/<lang>_silver.stats.json       derivation counts and split sizes

The UD train/dev/test files are pooled: splits here are by *lemma hash*, because the
question is generalization to unseen lemmas, not UD parsing. Only open-class POS are
used (NOUN, VERB, ADJ, AUX, PROPN, ADV for UD; all UniMorph entries).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from morphtok.analyzers.lemma_derived import (  # noqa: E402
    LemmaPair,
    build_silver,
    group_by_lemma,
    lemma_split,
    read_conllu,
    read_unimorph,
    write_silver_tsv,
)

OPEN = frozenset({"NOUN", "VERB", "ADJ", "AUX", "PROPN", "ADV", "V", "N"})
SOURCES = {
    "sd": {
        "ud": ["sd_isra-ud-train.conllu", "sd_isra-ud-dev.conllu", "sd_isra-ud-test.conllu"],
        "unimorph": [],
    },
    "ur": {
        "ud": ["ur_udtb-ud-train.conllu", "ur_udtb-ud-dev.conllu", "ur_udtb-ud-test.conllu"],
        "unimorph": ["urd.tsv"],
    },
}


def main() -> int:
    """Write silver TSV, held-out paradigms and statistics."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("lang", choices=sorted(SOURCES))
    ap.add_argument("--salt", default="morphtok-silver")
    ap.add_argument("--min-stem", type=int, default=2)
    a = ap.parse_args()
    pairs: list[LemmaPair] = []
    used: list[str] = []
    for f in SOURCES[a.lang]["ud"]:
        p = ROOT / "data" / "raw" / "ud" / f
        if p.exists():
            pairs += read_conllu(p, f"ud:{f.split('-')[0]}")
            used.append(p.relative_to(ROOT).as_posix())
    for f in SOURCES[a.lang]["unimorph"]:
        p = ROOT / "data" / "raw" / "unimorph" / f
        if p.exists():
            pairs += read_unimorph(p, "unimorph")
            used.append(p.relative_to(ROOT).as_posix())
    if not pairs:
        print("no input files found; see data/raw/SOURCE.md")
        return 2
    entries, stats = build_silver(pairs, a.salt, a.min_stem, OPEN)
    out = ROOT / "data" / "gold"
    split_counts = write_silver_tsv(
        entries,
        out / f"{a.lang}_silver.tsv",
        f"SILVER lemma-derived boundaries ({', '.join(used)}); not gold",
    )
    paradigms = {
        lem: {"split": lemma_split(lem, a.salt), "forms": sorted(forms)}
        for lem, forms in group_by_lemma(p for p in pairs if p.pos in OPEN).items()
        if lemma_split(lem, a.salt) in ("dev", "test") and len(forms) >= 2
    }
    (out / f"{a.lang}_paradigms_heldout.json").write_text(
        json.dumps(paradigms, ensure_ascii=False, indent=0), encoding="utf-8"
    )
    with_b = Counter(e.split for e in entries.values() if e.majority)
    summary = {
        "inputs": used,
        "salt": a.salt,
        "min_stem": a.min_stem,
        "derivation": dict(stats),
        "types_by_split": split_counts,
        "types_with_boundary_by_split": dict(with_b),
        "heldout_paradigms": len(paradigms),
        "mean_agreement": sum(e.agreement for e in entries.values()) / max(1, len(entries)),
    }
    (out / f"{a.lang}_silver.stats.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
