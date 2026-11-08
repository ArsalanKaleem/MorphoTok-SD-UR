"""sdnorm command line: build a Sindhi lexicon, normalize text, explain decisions.

    python scripts/sdnorm.py build-lexicon corpus.txt -o sd_lexicon.json
    python scripts/sdnorm.py normalize -l sd_lexicon.json < in.txt > out.txt
    python scripts/sdnorm.py explain -l sd_lexicon.json آھي کی ڪتاب کتاب

See ``src/morphtok/tools/sdnorm.py`` for the rules and ``docs/sdnorm.md`` for evaluation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from morphtok.tools.sdnorm import Normalizer, build_lexicon


def main() -> int:
    """CLI entry point."""
    for s in (sys.stdin, sys.stdout):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build-lexicon", help="count words in a UTF-8 corpus")
    b.add_argument("corpus", type=Path)
    b.add_argument("-o", "--out", type=Path, required=True)
    b.add_argument("--min-count", type=int, default=2)
    for name in ("normalize", "explain"):
        p = sub.add_parser(name)
        p.add_argument("-l", "--lexicon", type=Path, required=True)
        p.add_argument("--lex-ratio", type=float, default=50.0)
        p.add_argument("--lex-max-count", type=int, default=100)
        if name == "explain":
            p.add_argument("words", nargs="+")
    a = ap.parse_args()
    if a.cmd == "build-lexicon":
        with a.corpus.open(encoding="utf-8") as f:
            norm = Normalizer(build_lexicon(f))
        norm.save(a.out, a.min_count)
        print(f"wrote {a.out} ({sum(1 for n in norm.lexicon.values() if n >= a.min_count)} words)")
        return 0
    norm = Normalizer.load(a.lexicon, lex_ratio=a.lex_ratio, lex_max_count=a.lex_max_count)
    if a.cmd == "normalize":
        for line in sys.stdin:
            sys.stdout.write(norm.normalize(line))
        return 0
    for w in a.words:
        out = norm.normalize_word(w)
        print(
            f"{w} ({norm.lexicon.get(w, 0)}) -> {out} ({norm.lexicon.get(out, 0)})"
            + ("" if out != w else "  [kept]")
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
