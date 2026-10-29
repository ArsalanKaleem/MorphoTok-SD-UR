"""Silver boundary supervision derived from manually annotated (form, lemma) pairs.

Sources: UD treebanks (manual lemmas) and UniMorph paradigms. The *derivation* is a
documented heuristic, not linguistic analysis, so its output is **silver**:

* both strings are format-stripped (ZWNJ/ZWJ removed);
* ``form == lemma``             -> covered, no internal boundary;
* ``p = LCP(form, lemma)`` with ``min_stem <= p < len(form)`` -> one boundary at ``p``
  (stem | inflectional ending), e.g. lemma ``abcna``, form ``abcta`` -> ``abc|ta``;
* otherwise (suppletion, stem change, ``p < min_stem``) -> not derivable (uncovered).

Only suffixing inflection is captured; prefixes, compounds, clitics and stacked
suffixes are missed (recall-limited). Where one surface form receives different
boundary sets from different (form, lemma) pairs, every variant is kept as an
alternative analysis weighted by its count (ambiguity is reported, not resolved).

Leakage control: entries carry a ``split`` assigned **by lemma**. The analyzer used for
supervision must be built from ``train`` lemmas only, while dev/test lemmas serve as the
held-out silver evaluation set (see ``scripts/build_silver.py``).
"""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from morphtok.analyzers.base import Analysis, Analyzer
from morphtok.data.normalize import strip_format, unicode_normalize


@dataclass(frozen=True)
class LemmaPair:
    """One annotated (form, lemma) observation."""

    form: str
    lemma: str
    pos: str
    source: str


def derive_boundaries(form: str, lemma: str, min_stem: int = 2) -> tuple[int, ...] | None:
    """Boundary tuple for ``form`` given ``lemma`` (stripped coordinates), or ``None``."""
    f, _ = strip_format(unicode_normalize(form, "NFC"))
    lem, _ = strip_format(unicode_normalize(lemma, "NFC"))
    if not f or not lem or " " in f:
        return None
    if f == lem:
        return ()
    p = 0
    while p < min(len(f), len(lem)) and f[p] == lem[p]:
        p += 1
    if min_stem <= p < len(f):
        return (p,)
    return None


def lemma_split(lemma: str, salt: str, dev: float = 0.15, test: float = 0.15) -> str:
    """Deterministic train/dev/test assignment of a lemma (all its forms follow it)."""
    u = int.from_bytes(hashlib.sha256(f"{salt}|{lemma}".encode()).digest()[:8], "big") / 2**64
    if u < dev:
        return "dev"
    if u < dev + test:
        return "test"
    return "train"


def read_conllu(path: str | Path, source: str) -> list[LemmaPair]:
    """Word-level (form, lemma, UPOS) from a CoNLL-U file; multiword-token ranges skipped."""
    out: list[LemmaPair] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) < 4 or "-" in cols[0] or "." in cols[0]:
            continue
        if cols[2] in ("_", ""):
            continue
        out.append(LemmaPair(cols[1], cols[2], cols[3], source))
    return out


def read_unimorph(path: str | Path, source: str) -> list[LemmaPair]:
    """(form, lemma, POS) from a UniMorph TSV (lemma, form, features)."""
    out: list[LemmaPair] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        cols = line.split("\t")
        if len(cols) >= 3:
            out.append(LemmaPair(cols[1], cols[0], cols[2].split(";")[0], source))
    return out


@dataclass
class SilverEntry:
    """Aggregated silver analysis of one stripped surface form."""

    word: str
    variants: Counter[tuple[int, ...]]
    lemmas: set[str]
    split: str
    sources: set[str]

    @property
    def majority(self) -> tuple[int, ...]:
        """Most frequent boundary set (ties: fewer boundaries, then lexicographic)."""
        return min(self.variants, key=lambda b: (-self.variants[b], len(b), b))

    @property
    def agreement(self) -> float:
        """Share of observations agreeing with the majority boundary set."""
        return self.variants[self.majority] / sum(self.variants.values())


def build_silver(
    pairs: Iterable[LemmaPair], salt: str, min_stem: int = 2, open_classes: frozenset[str] | None = None
) -> tuple[dict[str, SilverEntry], Counter[str]]:
    """Aggregate pairs into silver entries; returns entries and derivation statistics.

    A surface form whose lemmas fall into different splits is assigned to the most
    restrictive one (test > dev > train) so held-out lemmas never leak into training.
    """
    stats: Counter[str] = Counter()
    entries: dict[str, SilverEntry] = {}
    rank = {"train": 0, "dev": 1, "test": 2}
    for pr in pairs:
        stats["pairs"] += 1
        if open_classes is not None and pr.pos not in open_classes:
            stats["skipped_pos"] += 1
            continue
        b = derive_boundaries(pr.form, pr.lemma, min_stem)
        if b is None:
            stats["not_derivable"] += 1
            continue
        stats["derived_with_boundary" if b else "derived_no_boundary"] += 1
        word = strip_format(unicode_normalize(pr.form, "NFC"))[0]
        lem = strip_format(unicode_normalize(pr.lemma, "NFC"))[0]
        split = lemma_split(lem, salt)
        e = entries.get(word)
        if e is None:
            e = entries[word] = SilverEntry(word, Counter(), set(), split, set())
        e.variants[b] += 1
        e.lemmas.add(lem)
        e.sources.add(pr.source)
        if rank[split] > rank[e.split]:
            e.split = split
    stats["types"] = len(entries)
    stats["ambiguous_types"] = sum(1 for e in entries.values() if len(e.variants) > 1)
    return entries, stats


class LemmaDerivedAnalyzer(Analyzer):
    """Analyzer over silver entries restricted to ``use_splits`` (default: train only).

    Confidence of a variant = ``base_confidence * count(variant) / count(all variants)``.
    ``base_confidence`` is an uncalibrated pilot constant (TODO: calibrate on gold).
    """

    name = "lemma_derived"

    def __init__(
        self,
        entries: dict[str, SilverEntry],
        use_splits: frozenset[str] = frozenset({"train"}),
        base_confidence: float = 0.8,
        version: str = "silver-1",
    ) -> None:
        self.entries = {w: e for w, e in entries.items() if e.split in use_splits}
        self.base_confidence = base_confidence
        self.version = version

    def analyze(self, word: str) -> list[Analysis]:
        """Weighted alternative analyses for a covered word, else ``[]``."""
        e = self.entries.get(word)
        if e is None:
            return []
        total = sum(e.variants.values())
        n = len(e.variants)
        return [
            Analysis(
                boundaries=b,
                confidence=self.base_confidence * c / total,
                source=f"silver:{'+'.join(sorted(e.sources))}",
                version=self.version,
                ambiguity=n,
            )
            for b, c in sorted(e.variants.items())
        ]


def write_silver_tsv(entries: dict[str, SilverEntry], path: Path, header: str) -> dict[str, int]:
    """Write ``word<TAB>boundaries<TAB>source<TAB>split`` (majority analysis) and counts."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [f"# {header}", "# word\tboundaries(majority, stripped coords)\tsource\tsplit"]
    counts: Counter[str] = Counter()
    for w in sorted(entries):
        e = entries[w]
        counts[e.split] += 1
        rows.append(f"{w}\t{','.join(map(str, e.majority))}\tsilver:{'+'.join(sorted(e.sources))}\t{e.split}")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    return dict(counts)


def load_silver_entries(path: str | Path) -> dict[str, SilverEntry]:
    """Reload a silver TSV as single-variant entries (majority analysis only)."""
    out: dict[str, SilverEntry] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        word, bounds, source, split = line.split("\t")
        b = tuple(int(x) for x in bounds.split(",") if x)
        out[word] = SilverEntry(word, Counter({b: 1}), set(), split, {source})
    return out


def merge_silver(sources: list[dict[str, SilverEntry]]) -> dict[str, SilverEntry]:
    """Union of several silver/gold word lists.

    A word present in several sources keeps every boundary variant (as weighted
    alternatives) and the most restrictive split (test > dev > train), so a word held
    out in any source is never used for supervision.
    """
    rank = {"train": 0, "dev": 1, "test": 2}
    out: dict[str, SilverEntry] = {}
    for src in sources:
        for w, e in src.items():
            cur = out.get(w)
            if cur is None:
                out[w] = SilverEntry(w, Counter(e.variants), set(e.lemmas), e.split, set(e.sources))
                continue
            cur.variants.update(e.variants)
            cur.lemmas |= e.lemmas
            cur.sources |= e.sources
            if rank.get(e.split, 0) > rank.get(cur.split, 0):
                cur.split = e.split
    return out


def group_by_lemma(pairs: Iterable[LemmaPair]) -> dict[str, set[str]]:
    """Lemma -> set of stripped single-word forms (for paradigm-coherence evaluation)."""
    out: dict[str, set[str]] = defaultdict(set)
    for pr in pairs:
        f = strip_format(unicode_normalize(pr.form, "NFC"))[0]
        if f and " " not in f:
            out[strip_format(unicode_normalize(pr.lemma, "NFC"))[0]].add(f)
    return dict(out)
