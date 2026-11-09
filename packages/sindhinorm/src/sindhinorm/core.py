"""sindhinorm: a corpus-guided, native-validated spelling normalizer for Sindhi (Arabic script).

Sindhi text typed on Urdu, Persian or Arabic keyboards mixes look-alike code points
(Farsi yeh ی for Sindhi ي, Urdu heh-goal ہ for ه, keheh ک or Arabic kaf ك for Sindhi ڪ) and
stray zero-width characters. Some of these are pure encoding variants; others are *different
Sindhi letters* (ک and ڪ are distinct letters: کي "to" vs ڪي "some"). A fixed character map
therefore either misses variants or corrupts real words.

sdnorm decides per **word**, using a frequency lexicon built from a Sindhi corpus:

* Letters are grouped into look-alike classes: yeh {ي ی ى ے}, heh {ه ھ ہ}, kaf {ڪ ک ك}.
* A word's candidate spellings are all combinations of class members at its class positions;
  the canonical spelling is the candidate most frequent in the lexicon.
* **Encoding-only** differences (ي/ی/ى, ه/ھ/ہ) are merged whenever the candidate is more
  frequent. A native reviewer judged these SAME in nearly all reviewed pairs.
* **Lexical** differences (any position involving ک, ڪ, ك or ے) are merged only when the
  rare form is at most ``lex_max_count`` times attested **and** the candidate is at least
  ``lex_ratio`` times more frequent, so that two real words (کي / ڪي) are never merged.
* Pairs a native reviewer judged DIFFERENT or UNSURE (``NATIVE_KEEP``) are never merged.
* Words absent from the lexicon get only the safest encoding folds (ی ى → ي, ہ → ه).
* Zero-width non-joiners/joiners that cannot affect shaping (next to a space, punctuation,
  a non-letter, a string edge, or another zero-width character) are removed; a ZWNJ between
  two letters is kept, because native review found those mark compound and ال-name joins.

Thresholds were fixed before evaluation. The evaluation (agreement with native judgements,
restoration of keyboard-substituted text) lives in the MorphoTok-SD-UR repository:
https://github.com/ArsalanKaleem/MorphoTok-SD-UR (``docs/sdnorm.md``).
"""

from __future__ import annotations

import gzip
import itertools
import json
import unicodedata
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

ZWNJ, ZWJ = "‌", "‍"
CLASSES: dict[str, str] = {
    "ي": "yeh", "ی": "yeh", "ى": "yeh", "ے": "yeh",
    "ه": "heh", "ھ": "heh", "ہ": "heh",
    "ڪ": "kaf", "ک": "kaf", "ك": "kaf",
}  # fmt: skip
MEMBERS: dict[str, tuple[str, ...]] = {
    "yeh": ("ي", "ی", "ى", "ے"),
    "heh": ("ه", "ھ", "ہ"),
    "kaf": ("ڪ", "ک", "ك"),
}
LEXICAL = frozenset("ڪکكے")  # letters whose substitution can change the word
SAFE_OOV = {"ی": "ي", "ى": "ي", "ہ": "ه"}  # encoding folds applied to unknown words
MAX_CANDIDATES = 4096

# Pairs (variant -> would-be canonical) that a native Sindhi reviewer judged DIFFERENT or
# UNSURE (review of 150 Wikipedia pairs, 2026-11-09; docs/findings_human_review.md §4).
NATIVE_KEEP: frozenset[tuple[str, str]] = frozenset({
    ("جے", "جي"), ("ڪي", "کي"), ("کے", "کي"), ("کی", "کي"), ("ڪان", "کان"), ("تہ", "ته"),
    ("تھ", "ته"), ("کري", "ڪري"), ("كيو", "ڪيو"), ("کيو", "ڪيو"), ("ہے", "هي"), ("کئی", "ڪئي"),
    ("كئي", "ڪئي"), ("کئي", "ڪئي"), ("ڪيس", "کيس"), ("شاھھ", "شاهه"), ("کن", "ڪن"), ("كن", "ڪن"),
    ("ڪجھھ", "ڪجهه"), ("ڪجھہ", "ڪجهه"), ("ڪجهھ", "ڪجهه"), ("ڏڪڻ", "ڏکڻ"), ("کو", "ڪو"), ("کيل", "ڪيل"),
})  # fmt: skip


def is_word_char(c: str) -> bool:
    """Letters and combining marks form words; ZWNJ/ZWJ are handled separately."""
    return unicodedata.category(c)[0] in "LM"


def clean_zero_width(text: str) -> str:
    """Drop ZWNJ/ZWJ unless it sits directly between two word characters (one kept per run)."""
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c not in (ZWNJ, ZWJ):
            out.append(c)
            i += 1
            continue
        j = i
        while j < n and text[j] in (ZWNJ, ZWJ):
            j += 1
        run = text[i:j]
        left = out[-1] if out else ""
        right = text[j] if j < n else ""
        if left and right and is_word_char(left) and is_word_char(right) and ZWNJ in run:
            # a non-joiner between letters can change shaping; keep exactly one
            if unicodedata.category(left) != "Mn" and unicodedata.category(right) != "Mn":
                out.append(ZWNJ)
        i = j
    return "".join(out)


def tokens(text: str) -> Iterator[tuple[bool, str]]:
    """Split into (is_word, chunk) pieces; a ZWNJ between letters stays inside the word."""
    buf: list[str] = []
    word = None
    for i, c in enumerate(text):
        inside = is_word_char(c) or (
            c == ZWNJ and buf and word and i + 1 < len(text) and is_word_char(text[i + 1])
        )
        w = bool(inside)
        if word is None or w == word:
            buf.append(c)
        else:
            yield bool(word), "".join(buf)
            buf = [c]
        word = w
    if buf:
        yield bool(word), "".join(buf)


def build_lexicon(lines: Iterable[str]) -> Counter[str]:
    """Word frequencies after zero-width cleanup."""
    c: Counter[str] = Counter()
    for ln in lines:
        c.update(w for is_w, w in tokens(clean_zero_width(unicodedata.normalize("NFC", ln))) if is_w)
    return c


@dataclass
class Normalizer:
    """Corpus-guided word normalizer (see module docstring)."""

    lexicon: Counter[str]
    lex_ratio: float = 50.0
    lex_max_count: int = 100
    keep: frozenset[tuple[str, str]] = NATIVE_KEEP
    _cache: dict[str, str] = field(default_factory=dict, repr=False)

    def candidates(self, word: str) -> Iterator[str]:
        """All spellings reachable by swapping look-alike letters (capped)."""
        slots = [MEMBERS[CLASSES[c]] if c in CLASSES else (c,) for c in word]
        if sum(len(s) > 1 for s in slots) > 8:
            yield word
            return
        for k, combo in enumerate(itertools.product(*slots)):
            if k >= MAX_CANDIDATES:
                return
            yield "".join(combo)

    def allowed(self, word: str, cand: str) -> bool:
        """Whether ``word`` may be rewritten as ``cand``."""
        if cand == word or (word, cand) in self.keep:
            return False
        f_w, f_c = self.lexicon.get(word, 0), self.lexicon.get(cand, 0)
        if f_c <= f_w:
            return False
        lexical = any(a != b and (a in LEXICAL or b in LEXICAL) for a, b in zip(word, cand, strict=True))
        if lexical:
            return f_w <= self.lex_max_count and f_c >= self.lex_ratio * max(f_w, 1)
        return True

    def decide(self, word: str) -> tuple[str, str]:
        """Canonical spelling of one word and the rule that produced it.

        Rules: ``no-variant-letters``, ``already-canonical`` (no more frequent variant),
        ``encoding-merge``, ``lexical-merge``, ``native-keep`` (blocked by a native judgement),
        ``lexical-guard`` (a more frequent variant exists but may be a different word),
        ``unknown-fold`` and ``unknown-kept`` (word not in the lexicon).
        """
        if not any(c in CLASSES for c in word):
            return word, "no-variant-letters"
        ranked = sorted(self.candidates(word), key=lambda x: -self.lexicon.get(x, 0))
        best = next((c for c in ranked if self.allowed(word, c)), word)
        if best != word:
            lexical = any(a != b and (a in LEXICAL or b in LEXICAL) for a, b in zip(word, best, strict=True))
            return best, "lexical-merge" if lexical else "encoding-merge"
        if self.lexicon.get(word, 0) == 0:
            folded = "".join(SAFE_OOV.get(c, c) for c in word)
            if folded != word and (word, folded) not in self.keep:
                return folded, "unknown-fold"
        top = next(
            (c for c in ranked if c != word and self.lexicon.get(c, 0) > self.lexicon.get(word, 0)), None
        )
        if top is not None:
            return word, "native-keep" if (word, top) in self.keep else "lexical-guard"
        return word, "unknown-kept" if self.lexicon.get(word, 0) == 0 else "already-canonical"

    def normalize_word(self, word: str) -> str:
        """Canonical spelling of one word."""
        if word not in self._cache:
            self._cache[word] = self.decide(word)[0]
        return self._cache[word]

    def explain(self, text: str) -> list[dict]:
        """Per-word decisions for ``text``: input, output, rule and lexicon counts."""
        text = clean_zero_width(unicodedata.normalize("NFC", text))
        out = []
        for is_w, w in tokens(text):
            if is_w:
                o, rule = self.decide(w)
                out.append({"word": w, "output": o, "rule": rule,
                            "count_in": self.lexicon.get(w, 0), "count_out": self.lexicon.get(o, 0)})  # fmt: skip
        return out

    def normalize(self, text: str) -> str:
        """NFC, zero-width cleanup, then per-word normalization."""
        text = clean_zero_width(unicodedata.normalize("NFC", text))
        return "".join(self.normalize_word(w) if is_w else w for is_w, w in tokens(text))

    def save(self, path: Path, min_count: int = 2) -> None:
        """Write the lexicon (counts ≥ ``min_count``) as JSON."""
        data = {w: n for w, n in self.lexicon.items() if n >= min_count}
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path, **kw: float) -> Normalizer:
        """Load a lexicon written by :meth:`save` (plain or ``.gz``)."""
        raw = path.read_bytes()
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return cls(Counter(json.loads(raw.decode("utf-8"))), **kw)  # type: ignore[arg-type]

    @classmethod
    def default(cls, **kw: float) -> Normalizer:
        """Normalizer with the bundled lexicon (Sindhi Wikipedia 2023-11-01, words seen ≥ 2 times)."""
        raw = resources.files("sindhinorm").joinpath("data/sd_lexicon.json.gz").read_bytes()
        return cls(Counter(json.loads(gzip.decompress(raw).decode("utf-8"))), **kw)  # type: ignore[arg-type]
