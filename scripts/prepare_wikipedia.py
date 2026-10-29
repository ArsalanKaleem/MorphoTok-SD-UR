"""Prepare a pilot text file from a parquet dump (Wikipedia by default; also FineWeb-2).

Input: ``data/raw/wikipedia_20231101/wiki_<lang>.parquet`` (Hugging Face dataset
``wikimedia/wikipedia``, config ``20231101.<lang>``; licence CC BY-SA 3.0 / GFDL).

Processing (every step counted in the manifest):

1. split each article's ``text`` on newlines (one paragraph = one line);
2. collapse internal whitespace; drop lines shorter than ``--min-chars``;
3. drop lines whose letters are less than ``--min-arabic`` Arabic-script
   (U+0600-06FF, U+0750-077F, U+08A0-08FF, U+FB50-FDFF, U+FE70-FEFF); this is a
   *script* filter, not a language identifier, so Sindhi pages may still contain
   Urdu/Persian text and vice versa (recorded as a limitation);
4. exact-duplicate removal;
5. deterministic sample of ``--n-lines`` lines: the lines with the smallest salted
   SHA-256 hashes (uniform, reproducible, independent of input order).

No Unicode normalization is applied here: the raw text is kept so the audit and the
normalization policies see what the source actually contains.

Added beyond the required tree to turn the first real corpus into the repository's
plain-text format with recorded provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
ARABIC_RANGES = ((0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF), (0xFB50, 0xFDFF), (0xFE70, 0xFEFF))
WS = re.compile(r"[ \t ]+")


def arabic_fraction(line: str) -> float:
    """Fraction of alphabetic characters that are in the Arabic-script blocks."""
    letters = [c for c in line if c.isalpha()]
    if not letters:
        return 0.0
    arab = sum(1 for c in letters if any(lo <= ord(c) <= hi for lo, hi in ARABIC_RANGES))
    return arab / len(letters)


def sha256_file(path: Path) -> str:
    """Hex SHA-256 of a file."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    """Write the pilot file and its manifest."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("lang", choices=["sd", "ur"])
    ap.add_argument("--n-lines", type=int, default=20000)
    ap.add_argument("--min-chars", type=int, default=20)
    ap.add_argument("--min-arabic", type=float, default=0.8)
    ap.add_argument("--salt", default="morphtok-wiki-pilot")
    ap.add_argument("--input", default=None, help="parquet with a 'text' column (default: Wikipedia dump)")
    ap.add_argument("--tag", default="wiki20231101", help="corpus tag used in the output file name")
    ap.add_argument("--source", default=None, help="source description for the manifest")
    ap.add_argument("--licence", default="CC BY-SA 3.0 / GFDL (as stated on the dataset card)")
    a = ap.parse_args()
    src = (
        Path(a.input).resolve()
        if a.input
        else ROOT / "data" / "raw" / "wikipedia_20231101" / f"wiki_{a.lang}.parquet"
    )
    table = pq.read_table(src, columns=["text"])
    counts = {"articles": table.num_rows, "paragraphs": 0, "too_short": 0, "low_arabic": 0, "duplicates": 0}
    seen: set[str] = set()
    kept: list[str] = []
    for text in table.column("text").to_pylist():
        for para in (text or "").split("\n"):
            counts["paragraphs"] += 1
            line = WS.sub(" ", para).strip()
            if len(line) < a.min_chars:
                counts["too_short"] += 1
                continue
            if arabic_fraction(line) < a.min_arabic:
                counts["low_arabic"] += 1
                continue
            if line in seen:
                counts["duplicates"] += 1
                continue
            seen.add(line)
            kept.append(line)
    counts["eligible_lines"] = len(kept)
    ranked = sorted(kept, key=lambda s: hashlib.sha256(f"{a.salt}|{s}".encode()).hexdigest())
    sample = ranked[: a.n_lines]
    out_dir = ROOT / "data" / "processed"
    out = out_dir / f"{a.lang}_{a.tag}_pilot{len(sample)}.txt"
    out.write_text("\n".join(sample) + "\n", encoding="utf-8", newline="\n")
    manifest = {
        "source": a.source
        or f"https://huggingface.co/datasets/wikimedia/wikipedia (config 20231101.{a.lang})",
        "licence": a.licence,
        "raw_file": src.relative_to(ROOT).as_posix(),
        "raw_sha256": sha256_file(src),
        "output": out.relative_to(ROOT).as_posix(),
        "output_sha256": sha256_file(out),
        "params": vars(a),
        "counts": {
            **counts,
            "sampled_lines": len(sample),
            "sampled_words": sum(len(s.split()) for s in sample),
        },
    }
    (out_dir / f"{out.stem}.manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(json.dumps(manifest, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
