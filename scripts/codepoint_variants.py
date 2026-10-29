"""Descriptive audit of visually confusable Arabic-script code points per corpus.

Counts occurrences, and words containing them, for groups of code points that render
alike or are commonly interchanged in digital text (yeh forms, kaf forms, heh forms,
plus ZWNJ for scale). It **does not** fold or normalize anything: which variants are
equivalent in Urdu or Sindhi orthography is a linguistic decision that needs
native-speaker approval (see the ``selective`` policy in ``data/normalize.py``).

Also reports *minimal-pair pressure*: how many word types have a counterpart type that
differs only by swapping one member of a group for another (e.g. the same word spelled
with U+064A and with U+06CC). These type splits inflate vocabulary and fertility
regardless of morphology.

Usage: ``python scripts/codepoint_variants.py <corpus.txt> [...]``; writes JSON next to
each input as ``<stem>.variants.json`` and prints a table.
"""

from __future__ import annotations

import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path

GROUPS: dict[str, tuple[str, ...]] = {
    "yeh": ("ي", "ی", "ى", "ے"),
    "kaf": ("ك", "ک", "ڪ"),
    "heh": ("ه", "ہ", "ھ", "ە"),
    "zwnj": ("‌",),
}


def main() -> int:
    """Audit each corpus file given on the command line."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    for arg in sys.argv[1:]:
        path = Path(arg)
        types: Counter[str] = Counter()
        n_words = 0
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                for w in line.split():
                    types[w] += 1
                    n_words += 1
        cp_tokens: Counter[str] = Counter()
        cp_words: Counter[str] = Counter()
        for w, f in types.items():
            for ch in set(w):
                if any(ch in g for g in GROUPS.values()):
                    cp_words[ch] += f
            for ch in w:
                if any(ch in g for g in GROUPS.values()):
                    cp_tokens[ch] += f
        pairs: dict[str, int] = {}
        for gname, members in GROUPS.items():
            if len(members) < 2:
                continue
            canon = {m: members[0] for m in members}
            folded: dict[str, set[str]] = {}
            for w in types:
                if any(m in w for m in members):
                    key = "".join(canon.get(c, c) for c in w)
                    folded.setdefault(key, set()).add(w)
            pairs[gname] = sum(1 for v in folded.values() if len(v) > 1)
        report = {
            "corpus": path.as_posix(),
            "n_words": n_words,
            "n_types": len(types),
            "codepoints": {
                f"U+{ord(ch):04X} {unicodedata.name(ch, '?')}": {
                    "tokens": cp_tokens[ch],
                    "words_containing_per_1k": round(1000 * cp_words[ch] / max(1, n_words), 3),
                }
                for g in GROUPS.values()
                for ch in g
            },
            "type_groups_with_variant_spellings": pairs,
        }
        path.with_name(path.stem + ".variants.json").write_text(
            json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8"
        )
        print(f"\n== {path.name}: {n_words} words, {len(types)} types")
        for name, v in report["codepoints"].items():
            print(f"  {name:<45} words/1k={v['words_containing_per_1k']:>9}  tokens={v['tokens']}")
        print("  type groups spelled with >1 variant:", pairs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
