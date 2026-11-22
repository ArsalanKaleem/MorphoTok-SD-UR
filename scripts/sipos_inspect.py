"""Describe the SiPOS file: structure, tags, and the spelling variation sindhinorm targets.

    python scripts/sipos_inspect.py "data/raw/sipos/SiPOS/SiPOS tagset.txt"

Exploratory; prints counts only.
"""

from __future__ import annotations

import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "sindhinorm" / "src"))

import sindhinorm

CHECK = {
    "Farsi yeh U+06CC": "ی", "alef maksura U+0649": "ى", "yeh barree U+06D2": "ے",
    "heh goal U+06C1": "ہ", "heh doachashmee U+06BE": "ھ",
    "keheh U+06A9": "ک", "Arabic kaf U+0643": "ك", "Sindhi kaf U+06AA": "ڪ",
    "ZWNJ U+200C": "‌", "ZWJ U+200D": "‍", "tatweel U+0640": "ـ",
}  # fmt: skip


def main() -> int:
    """Print the description."""
    lines = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
    header, rows = lines[0].split("\t"), lines[1:]
    blank = sum(1 for r in rows if not r.strip())
    recs = [r.split("\t") for r in rows if r.strip()]
    bad = [r for r in recs if len(r) != len(header)]
    print("header:", header, "| rows:", len(rows), "| blank:", blank, "| malformed:", len(bad), bad[:3])
    recs = [r for r in recs if len(r) == len(header)]
    tok = [r[0] for r in recs]
    upos = Counter(r[2] for r in recs)
    print("UPOS:", len(upos), dict(upos.most_common()))
    print("TAG (original):", len(Counter(r[1] for r in recs)))
    puncts = Counter(t for t, r in zip(tok, recs, strict=True) if r[2] in ("PUNCT", "SYM"))
    print("punctuation tokens:", dict(puncts.most_common(12)))
    enders = sum(1 for t in tok if t in ("۔", ".", "؟", "?", "!"))
    print(
        "sentence-final marks:", enders, "| mean tokens per sentence ~", round(len(tok) / max(enders, 1), 1)
    )
    chars = Counter(c for t in tok for c in t)
    print("--- code points of interest (token occurrences):")
    for name, c in CHECK.items():
        n = sum(1 for t in tok if c in t)
        print(f"  {name:26s} {n:7d} tokens ({n / len(tok):.2%})")
    pres = sum(1 for t in tok if any(0xFB50 <= ord(c) <= 0xFDFF or 0xFE70 <= ord(c) <= 0xFEFF for c in t))
    marks = sum(1 for t in tok if any(unicodedata.category(c) == "Mn" for c in t))
    nfc = sum(1 for t in tok if unicodedata.normalize("NFC", t) != t)
    latin = sum(1 for t in tok if any("a" <= c.lower() <= "z" for c in t))
    print(
        f"  presentation forms: {pres} tokens | combining marks: {marks} | not NFC: {nfc} | Latin letters: {latin}"
    )
    print("--- sindhinorm 0.1.0 on SiPOS tokens:")
    norm = sindhinorm.default_normalizer()
    changed = Counter()
    rules = Counter()
    for t in tok:
        out, rule = norm.decide(t) if any(c in sindhinorm.CLASSES for c in t) else (t, "no-variant-letters")
        rules[rule] += 1
        if out != t:
            changed[(t, out, rule)] += 1
    n_changed = sum(changed.values())
    print(f"  tokens changed: {n_changed} of {len(tok)} ({n_changed / len(tok):.2%}); types: {len(changed)}")
    print("  rules:", dict(rules.most_common()))
    print("  most frequent changes:")
    for (a, b, rule), n in changed.most_common(25):
        print(f"    {n:5d}  {a} -> {b}  [{rule}]")
    oov = sum(1 for t in tok if norm.lexicon.get(t, 0) == 0)
    print(f"  tokens not in the Wikipedia word list: {oov} ({oov / len(tok):.2%})")
    print(
        "  unknown chars:",
        sorted(c for c in chars if ord(c) > 127 and unicodedata.category(c)[0] not in "LMPZN")[:20],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
