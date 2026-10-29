"""Validate and import completed native-speaker review sheets (``data/audit/review/``).

* ``<lang>_boundaries.tsv`` -> ``data/gold/<lang>_human_dev.tsv`` (word, boundaries,
  ``human``, ``dev``). Rows whose letters changed, or that are marked ``SKIP``, are
  excluded and reported. Also reports agreement of the silver labels with the human ones.
* ``<lang>_zwnj.tsv`` -> MORPH rate with a Wilson CI, plus κ if there are several annotators.
* ``<lang>_letter_variants.tsv`` -> counts of SAME / DIFFERENT / UNSURE decisions and
  ``data/gold/<lang>_approved_variants.tsv`` (SAME pairs only).

Progress is reported per sheet; partially completed sheets are fine.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from audit.agreement import adjudicate, pairwise_report  # noqa: E402

from morphtok.eval.morph_boundary import boundary_prf  # noqa: E402
from morphtok.unicode_audit.contexts import load_annotations, morph_rate  # noqa: E402

REVIEW = ROOT / "data" / "audit" / "review"
GOLD = ROOT / "data" / "gold"
DECISIONS = ("SAME", "DIFFERENT", "UNSURE")


def rel(p: Path) -> str:
    """Path relative to the repository when possible."""
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def read_rows(path: Path) -> tuple[list[str], list[list[str]]]:
    """Header and rows of a (possibly BOM-prefixed) TSV; short rows are padded."""
    lines = [ln for ln in path.read_text(encoding="utf-8-sig").splitlines() if ln.strip()]
    header = lines[0].split("\t")
    rows = []
    for ln in lines[1:]:
        cols = ln.split("\t")
        rows.append(cols + [""] * (len(header) - len(cols)))
    return header, rows


def segmentation_to_boundaries(word: str, seg: str) -> tuple[int, ...] | None:
    """Positions of ``+`` marks, or ``None`` if the letters differ from ``word``."""
    seg = seg.strip().replace(" ", "")
    if seg.replace("+", "") != word or seg.startswith("+") or seg.endswith("+") or "++" in seg:
        return None
    out, pos = [], 0
    for piece in seg.split("+")[:-1]:
        pos += len(piece)
        out.append(pos)
    return tuple(out)


def ingest_boundaries(lang: str) -> None:
    """Import Task 1."""
    path = REVIEW / f"{lang}_boundaries.tsv"
    if not path.exists():
        return
    header, rows = read_rows(path)
    ix = {h: i for i, h in enumerate(header)}
    good: list[tuple[str, tuple[int, ...], bool]] = []
    problems: list[str] = []
    status_count: Counter[str] = Counter()
    for r in rows:
        word, seg = r[ix["word"]].strip(), r[ix["segmentation"]].strip()
        status = r[ix["status"]].strip().upper()
        status_count[status or "(not reviewed)"] += 1
        if not status or status == "SKIP":
            continue
        if status not in ("OK", "?"):
            problems.append(f"  {r[ix['item_id']]}: status must be OK, ? or SKIP (got {status!r})")
            continue
        b = segmentation_to_boundaries(word, seg)
        if b is None:
            problems.append(f"  {r[ix['item_id']]}: letters of {seg!r} differ from {word!r} (only add '+')")
            continue
        good.append((word, b, status == "?"))
    print(f"\n[{lang} boundaries] {len(rows)} rows; {dict(status_count)}; problems {len(problems)}")
    for p in problems[:30]:
        print(p)
    if not good:
        print("  nothing reviewed yet")
        return
    out = GOLD / f"{lang}_human_dev.tsv"
    lines = ["# HUMAN gold (native-speaker review, dev split)", "# word\tboundaries\tsource\tsplit"]
    lines += [f"{w}\t{','.join(map(str, b))}\thuman{'-unsure' if u else ''}\tdev" for w, b, u in good]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"  wrote {rel(out)} ({len(good)} reviewed words)")
    silver = {}
    sp = GOLD / f"{lang}_silver.tsv"
    if sp.exists():
        for ln in sp.read_text(encoding="utf-8").splitlines():
            if ln and not ln.startswith("#"):
                w, bs, _s, _sp = ln.split("\t")
                silver[w] = {int(x) for x in bs.split(",") if x}
    pairs = [(silver[w], set(b)) for w, b, _u in good if w in silver]
    if pairs:
        r = boundary_prf([p for p, _ in pairs], [g for _, g in pairs])
        print(f"  silver vs human on {len(pairs)} words: P={r['precision']} R={r['recall']} F1={r['f1']}")


def ingest_zwnj(lang: str) -> None:
    """Import Task 2."""
    path = REVIEW / f"{lang}_zwnj.tsv"
    if not path.exists():
        return
    try:
        ratings = load_annotations(path)
    except ValueError as e:
        print(f"\n[{lang} zwnj] PROBLEM: {e}")
        return
    _, rows = read_rows(path)
    print(f"\n[{lang} zwnj] labelled {len(ratings)} of {len(rows)} occurrences")
    if not ratings:
        return
    rate = morph_rate(adjudicate(ratings))
    print(
        f"  counts {rate['counts']}; MORPH rate {rate['morph_rate']} (Wilson 95% {rate['wilson_95']}), n={rate['denominator']}"
    )
    rep = pairwise_report(ratings)
    if len(rep["annotators"]) > 1:
        print(f"  agreement: {rep['pairs']}")


def ingest_variants(lang: str) -> None:
    """Import Task 3."""
    path = REVIEW / f"{lang}_letter_variants.tsv"
    if not path.exists():
        return
    header, rows = read_rows(path)
    ix = {h: i for i, h in enumerate(header)}
    c: Counter[str] = Counter()
    bad = []
    same_rows = []
    for r in rows:
        d = r[ix["decision"]].strip().upper()
        if not d:
            continue
        if d not in DECISIONS:
            bad.append(f"  {r[ix['pair_id']]}: unknown decision {d!r}")
            continue
        c[d] += 1
        if d == "SAME":
            a = r[ix["spelling_A (count)"]].rsplit(" (", 1)[0]
            b = r[ix["spelling_B (count)"]].rsplit(" (", 1)[0]
            same_rows.append("\t".join([r[ix["pair_id"]], a, b, r[ix["note"]]]))
    print(
        f"\n[{lang} letter variants] decided {sum(c.values())} of {len(rows)}: {dict(c)}; problems {len(bad)}"
    )
    for b in bad[:30]:
        print(b)
    if same_rows:
        out = GOLD / f"{lang}_approved_variants.tsv"
        out.write_text(
            "pair_id\tspelling_A\tspelling_B\tnote\n" + "\n".join(same_rows) + "\n", encoding="utf-8"
        )
        print(f"  wrote {rel(out)}")


def main() -> int:
    """Check every sheet that exists."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    if not REVIEW.exists():
        print("no review sheets; run scripts/make_review_sheets.py first")
        return 1
    for lang in ("sd", "ur"):
        ingest_boundaries(lang)
        ingest_zwnj(lang)
        ingest_variants(lang)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
