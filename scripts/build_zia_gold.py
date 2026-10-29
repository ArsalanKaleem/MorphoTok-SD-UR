"""Human-annotated Urdu sub-word boundaries from the ZWNJ-annotated corpus of Zia et al.

Source: ``data/raw/zia2018/data_diacritized.txt`` (Zia, Raza & Athar, COLING 2018;
data CC BY 4.0). In that corpus annotators placed ZWNJ at *sub-word* boundaries
(compounds, affixation, reduplication) following normative orthography rules.

For every space-delimited word containing ZWNJ:

* Arabic diacritics (U+064B-U+065F, U+0670) are removed, because the tokenizers are
  trained on mostly undiacritized text; boundary positions are remapped accordingly;
* ZWNJ positions become boundaries in the stripped, undiacritized word;
* types are split train/dev/test by a salted hash of the stripped word.

Output: ``data/gold/ur_zia_zwnj.tsv`` (``word, boundaries, source, split``) and stats.

Only ZWNJ-marked boundaries are annotated (not inflectional endings), so against this
set **recall** is meaningful; precision and F1 are not (unannotated true boundaries
count as false positives).
"""

from __future__ import annotations

import hashlib
import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZWNJ = "‌"
SALT = "morphtok-zia"


def is_diacritic(ch: str) -> bool:
    """Arabic harakat, tanwin, shadda, sukun and related marks, plus superscript alef."""
    o = ord(ch)
    return 0x064B <= o <= 0x065F or o == 0x0670


def word_split(word: str) -> str:
    """Deterministic 70/15/15 split of a word type."""
    u = int.from_bytes(hashlib.sha256(f"{SALT}|{word}".encode()).digest()[:8], "big") / 2**64
    return "dev" if u < 0.15 else "test" if u < 0.30 else "train"


def main() -> int:
    """Write the gold TSV and statistics."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    src = ROOT / "data" / "raw" / "zia2018" / "data_diacritized.txt"
    text = unicodedata.normalize("NFC", src.read_text(encoding="utf-8-sig"))
    stats: Counter[str] = Counter()
    gold: dict[str, Counter[tuple[int, ...]]] = {}
    for raw in text.split():
        stats["words"] += 1
        if ZWNJ not in raw:
            continue
        stats["words_with_zwnj"] += 1
        chars: list[str] = []
        bounds: list[int] = []
        for ch in raw:
            if ch == ZWNJ:
                if chars and (not bounds or bounds[-1] != len(chars)):
                    bounds.append(len(chars))
            elif not is_diacritic(ch) and unicodedata.category(ch) != "Cf":
                chars.append(ch)
        word = "".join(chars)
        b = tuple(x for x in bounds if 0 < x < len(word))
        if not b:
            stats["edge_zwnj_only"] += 1
            continue
        gold.setdefault(word, Counter())[b] += 1
    rows = [
        "# GOLD (human ZWNJ sub-word annotation, Zia et al. 2018, CC BY 4.0); diacritics removed",
        "# word\tboundaries\tsource\tsplit",
    ]
    splits: Counter[str] = Counter()
    conflicts = 0
    for w in sorted(gold):
        variants = gold[w]
        conflicts += len(variants) > 1
        b = min(variants, key=lambda x: (-variants[x], x))
        sp = word_split(w)
        splits[sp] += 1
        rows.append(f"{w}\t{','.join(map(str, b))}\tzia2018\t{sp}")
    out = ROOT / "data" / "gold" / "ur_zia_zwnj.tsv"
    out.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    summary = {
        **dict(stats),
        "types": len(gold),
        "types_by_split": dict(splits),
        "conflicting_types": conflicts,
        "zwnj_per_100_words": round(100 * text.count(ZWNJ) / max(1, stats["words"]), 3),
    }
    (ROOT / "data" / "gold" / "ur_zia_zwnj.stats.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8"
    )
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
