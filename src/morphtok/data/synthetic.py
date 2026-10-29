"""Deterministic SYNTHETIC corpus generator (integration tests and demos only).

The corpus uses an artificial Latin-letter "language" with invented stems and affixes.
It makes **no claim** about Sindhi or Urdu. ZWNJ/ZWJ are inserted by fixed,
documented probabilities so that code paths for format characters are exercised and
the ground truth is known by construction:

* ZWNJ at a morpheme join with probability ``p_zwnj_morph``;
* ZWNJ at a non-morpheme interior position with probability ``p_zwnj_other``;
* a doubled ZWNJ with probability ``p_double`` (given a ZWNJ is inserted);
* ZWJ at an interior position with probability ``p_zwj``.

Gold boundaries are morpheme joins in **format-stripped** coordinates.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

ZWNJ = "‌"
ZWJ = "‍"
CONSONANTS = "ptkbdgmnslrvzf"
VOWELS = "aeiou"


@dataclass(frozen=True)
class SyntheticSpec:
    """All generator parameters (the defaults define the committed fixture)."""

    seed: int = 20261025
    n_lines: int = 1000
    n_stems: int = 80
    n_prefixes: int = 3
    n_suffixes: int = 8
    min_words: int = 4
    max_words: int = 12
    p_prefix: float = 0.2
    p_suffix1: float = 0.6
    p_suffix2: float = 0.25
    p_zwnj_morph: float = 0.2
    p_zwnj_other: float = 0.01
    p_double: float = 0.05
    p_zwj: float = 0.005
    zipf_s: float = 1.1


def _syllables(rng: random.Random, k: int) -> str:
    return "".join(rng.choice(CONSONANTS) + rng.choice(VOWELS) for _ in range(k))


def _inventory(rng: random.Random, n: int, lo: int, hi: int, used: set[str]) -> list[str]:
    out: list[str] = []
    while len(out) < n:
        s = _syllables(rng, rng.randint(lo, hi))
        if s not in used:
            used.add(s)
            out.append(s)
    return out


@dataclass(frozen=True)
class SyntheticCorpus:
    """Generated lines plus gold segmentations (stripped word -> boundaries)."""

    lines: list[str]
    gold: dict[str, tuple[int, ...]]
    spec: SyntheticSpec


def generate(spec: SyntheticSpec | None = None) -> SyntheticCorpus:
    """Generate the corpus deterministically from ``spec.seed``."""
    spec = spec or SyntheticSpec()
    rng = random.Random(spec.seed)
    used: set[str] = set()
    stems = _inventory(rng, spec.n_stems, 1, 3, used)
    prefixes = _inventory(rng, spec.n_prefixes, 1, 1, used)
    suffixes = [s[:-1] if rng.random() < 0.3 else s for s in _inventory(rng, spec.n_suffixes, 1, 1, used)]
    weights = [1.0 / (r + 1) ** spec.zipf_s for r in range(len(stems))]
    gold: dict[str, tuple[int, ...]] = {}
    lines: list[str] = []
    while len(lines) < spec.n_lines:
        words: list[str] = []
        for _ in range(rng.randint(spec.min_words, spec.max_words)):
            morphs: list[str] = []
            if rng.random() < spec.p_prefix:
                morphs.append(rng.choice(prefixes))
            morphs.append(rng.choices(stems, weights)[0])
            if rng.random() < spec.p_suffix1:
                morphs.append(rng.choice(suffixes))
                if rng.random() < spec.p_suffix2:
                    morphs.append(rng.choice(suffixes))
            stripped = "".join(morphs)
            bounds: list[int] = []
            pos = 0
            for m in morphs[:-1]:
                pos += len(m)
                bounds.append(pos)
            if stripped in gold and gold[stripped] != tuple(bounds):
                continue  # avoid surface ambiguity in the fixture
            gold[stripped] = tuple(bounds)
            out: list[str] = []
            for i, ch in enumerate(stripped):
                if i > 0:
                    p = spec.p_zwnj_morph if i in bounds else spec.p_zwnj_other
                    if rng.random() < p:
                        out.append(ZWNJ * (2 if rng.random() < spec.p_double else 1))
                    elif rng.random() < spec.p_zwj:
                        out.append(ZWJ)
                out.append(ch)
            words.append("".join(out))
        lines.append(" ".join(words))
    return SyntheticCorpus(lines=lines, gold=gold, spec=spec)


def gold_split(word: str, seed: int, dev_fraction: float = 0.5) -> str:
    """Deterministic dev/test assignment of a gold word *type*."""
    r = random.Random(f"{seed}|split|{word}").random()
    return "dev" if r < dev_fraction else "test"


def write_fixture(directory: Path, spec: SyntheticSpec | None = None) -> None:
    """Write ``SYNTHETIC_corpus.txt`` and ``SYNTHETIC_gold.tsv`` into ``directory``."""
    corpus = generate(spec)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "SYNTHETIC_corpus.txt").write_text(
        "\n".join(corpus.lines) + "\n", encoding="utf-8", newline="\n"
    )
    rows = ["# SYNTHETIC gold: word<TAB>boundaries(stripped coords)<TAB>source<TAB>split"]
    for w in sorted(corpus.gold):
        b = ",".join(map(str, corpus.gold[w]))
        rows.append(f"{w}\t{b}\tSYNTHETIC\t{gold_split(w, corpus.spec.seed)}")
    (directory / "SYNTHETIC_gold.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    write_fixture(Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "synthetic")
