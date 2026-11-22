"""Command line: ``sindhinorm`` (normalize stdin or files), ``sindhinorm explain``, ``build-lexicon``.

sindhinorm < in.txt > out.txt
sindhinorm input.txt -o output.txt
sindhinorm explain "هي ڪتاب آهی"
sindhinorm build-lexicon corpus.txt -o my_lexicon.json.gz
sindhinorm -l my_lexicon.json.gz < in.txt
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

from . import __version__
from .core import Normalizer, build_lexicon


def _load(a: argparse.Namespace) -> Normalizer:
    kw = {"lex_ratio": a.lex_ratio, "lex_max_count": a.lex_max_count, "mode": a.mode, "fold_heh": a.fold_heh}
    return Normalizer.load(a.lexicon, **kw) if a.lexicon else Normalizer.default(**kw)


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    for s in (sys.stdin, sys.stdout):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv.pop(0) if argv and argv[0] in ("explain", "build-lexicon") else "normalize"
    ap = argparse.ArgumentParser(prog=f"sindhinorm {cmd}".replace(" normalize", ""), description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)  # fmt: skip
    ap.add_argument("--version", action="version", version=f"sindhinorm {__version__}")
    if cmd == "build-lexicon":
        ap.add_argument("corpus", type=Path)
        ap.add_argument("-o", "--out", type=Path, required=True)
        ap.add_argument("--min-count", type=int, default=2)
        a = ap.parse_args(argv)
        with a.corpus.open(encoding="utf-8") as f:
            lex = build_lexicon(f)
        data = json.dumps({w: n for w, n in lex.most_common() if n >= a.min_count}, ensure_ascii=False)
        raw = data.encode("utf-8")
        a.out.write_bytes(gzip.compress(raw) if a.out.suffix == ".gz" else raw)
        print(f"wrote {a.out} ({sum(n >= a.min_count for n in lex.values())} words)", file=sys.stderr)
        return 0
    ap.add_argument("-l", "--lexicon", type=Path, default=None, help="custom lexicon (default: bundled)")
    ap.add_argument("--lex-ratio", type=float, default=50.0)
    ap.add_argument("--lex-max-count", type=int, default=100)
    ap.add_argument("--mode", choices=["keyboard", "frequency"], default="keyboard",
                    help="keyboard (default): fix only letters typed on Urdu/Persian/Arabic keyboards; "
                    "frequency: the 0.1.0 rules")  # fmt: skip
    ap.add_argument("--fold-heh", action="store_true", help="keyboard mode: also merge ه/ھ spellings")
    if cmd == "explain":
        ap.add_argument("text", nargs="+")
        ap.add_argument("--json", action="store_true")
        a = ap.parse_args(argv)
        rows = _load(a).explain(" ".join(a.text))
        if a.json:
            print(json.dumps(rows, ensure_ascii=False, indent=1))
        else:
            for r in rows:
                arrow = "->" if r["output"] != r["word"] else "=="
                print(
                    f"{r['word']} ({r['count_in']}) {arrow} {r['output']} ({r['count_out']})  [{r['rule']}]"
                )
        return 0
    ap.add_argument("inputs", nargs="*", type=Path, help="files (default: stdin)")
    ap.add_argument("-o", "--out", type=Path, default=None)
    a = ap.parse_args(argv)
    norm = _load(a)
    out = a.out.open("w", encoding="utf-8", newline="") if a.out else sys.stdout
    try:
        for src in a.inputs or [None]:
            f = src.open(encoding="utf-8", newline="") if src else sys.stdin
            for line in f:
                out.write(norm.normalize(line))
    finally:
        if a.out:
            out.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
