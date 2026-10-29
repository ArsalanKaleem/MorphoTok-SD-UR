"""Inter-annotator agreement and adjudication for the ZWNJ and boundary audits.

Standard-library only so annotators can run it without the full environment::

    python audit/agreement.py data/audit/<sheet>.tsv

Implements Cohen's kappa (two annotators), Fleiss' kappa (any fixed number of raters
per item) and a documented adjudication rule (strict majority; otherwise ``AMBIG``
pending adjudicator review). Kappa is ``None`` when undefined (e.g. a single label).
"""

from __future__ import annotations

import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path


def cohen_kappa(a: Sequence[str], b: Sequence[str]) -> float | None:
    """Cohen's kappa for two aligned label sequences."""
    if len(a) != len(b):
        raise ValueError("label sequences must be aligned")
    n = len(a)
    if n == 0:
        return None
    po = sum(1 for x, y in zip(a, b, strict=True) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return None if pe == 1.0 else (po - pe) / (1 - pe)


def fleiss_kappa(items: Sequence[Sequence[str]]) -> float | None:
    """Fleiss' kappa; every item must have the same number (>= 2) of ratings."""
    if not items:
        return None
    m = len(items[0])
    if m < 2 or any(len(r) != m for r in items):
        raise ValueError("Fleiss' kappa needs the same number (>=2) of ratings per item")
    n = len(items)
    cats = sorted({lab for r in items for lab in r})
    p_j = {c: sum(r.count(c) for r in items) / (n * m) for c in cats}
    p_i = [(sum(r.count(c) ** 2 for c in cats) - m) / (m * (m - 1)) for r in items]
    p_bar = sum(p_i) / n
    pe = sum(v * v for v in p_j.values())
    return None if pe == 1.0 else (p_bar - pe) / (1 - pe)


def adjudicate(ratings: Mapping[str, Sequence[tuple[str, str]]]) -> dict[str, str]:
    """Strict-majority label per item; ties become ``AMBIG`` (flagged for an adjudicator)."""
    out: dict[str, str] = {}
    for item, rs in ratings.items():
        c = Counter(lab for _, lab in rs)
        (top, k), *_rest = c.most_common()
        out[item] = top if k > len(rs) / 2 else "AMBIG"
    return out


def pairwise_report(ratings: Mapping[str, Sequence[tuple[str, str]]]) -> dict[str, object]:
    """Cohen's kappa for every annotator pair over their shared items."""
    annotators = sorted({a for rs in ratings.values() for a, _ in rs})
    pairs: dict[str, object] = {}
    for i, x in enumerate(annotators):
        for y in annotators[i + 1 :]:
            la, lb = [], []
            for rs in ratings.values():
                d = dict(rs)
                if x in d and y in d:
                    la.append(d[x])
                    lb.append(d[y])
            pairs[f"{x}~{y}"] = {"n_shared": len(la), "cohen_kappa": cohen_kappa(la, lb)}
    return {"annotators": annotators, "pairs": pairs}


def _load(path: Path) -> dict[str, list[tuple[str, str]]]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    idx = {h: i for i, h in enumerate(lines[0].split("\t"))}
    out: dict[str, list[tuple[str, str]]] = {}
    for ln in lines[1:]:
        cols = ln.split("\t")
        if cols[idx["label"]].strip():
            out.setdefault(cols[idx["occ_id"]], []).append((cols[idx["annotator"]], cols[idx["label"]]))
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python audit/agreement.py <annotation_sheet.tsv>")
    r = _load(Path(sys.argv[1]))
    print(pairwise_report(r))
    print(Counter(adjudicate(r).values()))
