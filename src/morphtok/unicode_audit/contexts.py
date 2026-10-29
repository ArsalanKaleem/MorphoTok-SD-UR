"""ZWNJ occurrence extraction, stratified annotation sampling, and annotation scoring.

Implements ``audit/sampling_protocol.md``. The sampling frame is every ZWNJ run in the
canonical corpus; strata are (left class, right class, position in word). Sampling is
deterministic given the seed.

Annotation labels (``audit/annotation_guidelines.md``):
``MORPH`` (ZWNJ coincides with a morphological boundary), ``ORTHO`` (orthographic
only), ``AMBIG`` (annotator cannot decide), ``ERROR`` (encoding/typing error),
``FOREIGN`` (the text is not in the target language, e.g. Persian quoted in Urdu).
"""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from morphtok.data.normalize import ZWNJ, strip_format, unicode_normalize
from morphtok.eval.stats import wilson_interval
from morphtok.unicode_audit.zwnj_stats import char_class, position_in_word

LABELS: tuple[str, ...] = ("MORPH", "ORTHO", "AMBIG", "ERROR", "FOREIGN")


@dataclass(frozen=True)
class ZwnjOccurrence:
    """One ZWNJ run in context."""

    occ_id: str
    line_no: int
    word: str
    char_index: int
    stripped_position: int
    left_context: str
    right_context: str
    stratum: str


def extract_occurrences(
    lines: Iterable[str], unicode_form: str = "NFC", window: int = 20
) -> list[ZwnjOccurrence]:
    """Every ZWNJ run with its word, stripped position, KWIC context and stratum."""
    out: list[ZwnjOccurrence] = []
    for ln, raw in enumerate(lines):
        line = unicode_normalize(raw, unicode_form)
        offset = 0
        for word in line.split():
            start = line.index(word, offset)
            offset = start + len(word)
            _, cmap = strip_format(word)
            i = 0
            while i < len(word):
                if word[i] != ZWNJ:
                    i += 1
                    continue
                j = i
                while j < len(word) and word[j] == ZWNJ:
                    j += 1
                left = word[i - 1] if i > 0 else ""
                right = word[j] if j < len(word) else ""
                stratum = f"{char_class(left)}|{char_class(right)}|{position_in_word(i, word)}"
                abs_i = start + i
                out.append(
                    ZwnjOccurrence(
                        occ_id=f"L{ln}C{abs_i}",
                        line_no=ln,
                        word=word,
                        char_index=i,
                        stripped_position=cmap[i],
                        left_context=line[max(0, abs_i - window) : abs_i],
                        right_context=line[abs_i : abs_i + window],
                        stratum=stratum,
                    )
                )
                i = j
    return out


def stratified_sample(
    occs: list[ZwnjOccurrence], n_total: int, seed: int, min_per_stratum: int = 1
) -> list[ZwnjOccurrence]:
    """Proportional allocation with a per-stratum minimum; deterministic given ``seed``."""
    rng = random.Random(seed)
    by: dict[str, list[ZwnjOccurrence]] = {}
    for o in occs:
        by.setdefault(o.stratum, []).append(o)
    total = len(occs)
    sample: list[ZwnjOccurrence] = []
    for stratum in sorted(by):
        items = by[stratum]
        k = max(min_per_stratum, round(n_total * len(items) / total)) if total else 0
        sample.extend(rng.sample(items, min(k, len(items))))
    return sample


def write_annotation_sheet(sample: list[ZwnjOccurrence], path: Path) -> None:
    """TSV for annotators; the ``label`` and ``annotator`` columns are left empty."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = ["occ_id\tstratum\tword\tchar_index\tleft_context\tright_context\tlabel\tannotator\tnote"]
    for o in sample:
        left = o.left_context.replace("\t", " ")
        right = o.right_context.replace("\t", " ").replace(ZWNJ, "<ZWNJ>", 1)
        rows.append(f"{o.occ_id}\t{o.stratum}\t{o.word}\t{o.char_index}\t{left}\t{right}\t\t\t")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")


def load_annotations(path: Path) -> dict[str, list[tuple[str, str]]]:
    """``occ_id -> [(annotator, label), ...]`` from a completed sheet."""
    out: dict[str, list[tuple[str, str]]] = {}
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    header = lines[0].split("\t")
    idx = {h: i for i, h in enumerate(header)}
    for line in lines[1:]:
        cols = line.split("\t")
        cols += [""] * (len(header) - len(cols))  # spreadsheet apps drop empty trailing cells
        label = cols[idx["label"]].strip().upper()
        if label:
            if label not in LABELS:
                raise ValueError(f"unknown label {label!r} in {path}")
            annotator = cols[idx["annotator"]].strip() or "A1"
            out.setdefault(cols[idx["occ_id"]], []).append((annotator, label))
    return out


def morph_rate(labels: Mapping[str, str]) -> dict[str, object]:
    """Proportion of adjudicated occurrences labelled MORPH, with a Wilson 95% CI.

    The denominator excludes ``ERROR`` and ``FOREIGN``; ``AMBIG`` is reported and
    *included* in the denominator (conservative for the claim that ZWNJ marks morphology).
    """
    c = Counter(labels.values())
    denom = c["MORPH"] + c["ORTHO"] + c["AMBIG"]
    return {
        "counts": dict(c),
        "denominator": denom,
        "morph_rate": c["MORPH"] / denom if denom else None,
        "wilson_95": wilson_interval(c["MORPH"], denom),
    }


def oracle_labels_from_gold(
    occs: Iterable[ZwnjOccurrence], gold: Mapping[str, tuple[int, ...]]
) -> dict[str, str]:
    """SYNTHETIC-ONLY: label occurrences from construction-time gold boundaries."""
    out: dict[str, str] = {}
    for o in occs:
        stripped, _ = strip_format(o.word)
        if stripped in gold:
            out[o.occ_id] = "MORPH" if o.stripped_position in gold[stripped] else "ORTHO"
    return out
