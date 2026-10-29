"""Unicode and format-character normalization policies with explicit index maps.

Pipeline (each step documented, none assumed linguistically correct):

1. **Unicode normalization** (``none`` | ``NFC`` | ``NFKC``) of the raw text gives the
   *canonical* text. Gold annotations are defined on canonical words.
2. **Format-character policy** for ZWNJ (U+200C), applied per canonical word:

   ``preserve``        keep ZWNJ as an ordinary character.
   ``remove``          delete ZWNJ.
   ``boundary_marker`` delete ZWNJ and record its position as a forced pre-token
                       split (an orthographic hard boundary, *not* a morphological
                       claim).
   ``selective``       apply only explicitly approved context rules; with no rules
                       configured this is identical to ``preserve`` and a warning is
                       emitted.

Evaluation coordinate space
---------------------------
All boundary metrics are computed in the **format-stripped coordinate space** of the
canonical word: the word with every character in ``EVAL_FORMAT_CHARS`` removed. A
boundary on either side of a run of such characters collapses to one stripped
position. This puts all policies in one comparable space; it is a measurement
convention, not a claim that ZWNJ and ZWJ behave alike.

Orthographic words are whitespace-delimited tokens of the *raw* text, so fertility
denominators are identical across policies.
"""

from __future__ import annotations

import unicodedata
import warnings
from dataclasses import dataclass, field
from enum import StrEnum

ZWNJ: str = "‌"
ZWJ: str = "‍"
EVAL_FORMAT_CHARS: frozenset[str] = frozenset({ZWNJ, ZWJ})


class ZwnjPolicy(StrEnum):
    """Format-character policy for U+200C."""

    PRESERVE = "preserve"
    REMOVE = "remove"
    BOUNDARY_MARKER = "boundary_marker"
    SELECTIVE = "selective"


@dataclass(frozen=True)
class SelectiveRule:
    """An explicitly approved ZWNJ context rule (none ship with this repository).

    ``left``/``right`` are sets of characters; a ZWNJ whose neighbours match is
    handled by ``action`` (``remove`` or ``boundary``). Rules must cite ``approved_by``.
    """

    left: frozenset[str]
    right: frozenset[str]
    action: str
    approved_by: str

    def matches(self, left: str, right: str) -> bool:
        """Whether this rule applies to a ZWNJ between ``left`` and ``right``."""
        return left in self.left and right in self.right


@dataclass
class NormalizationPolicy:
    """Complete, hashable description of how text is normalized before tokenization."""

    unicode_form: str = "NFC"
    zwnj: ZwnjPolicy = ZwnjPolicy.PRESERVE
    selective_rules: list[SelectiveRule] = field(default_factory=list)

    def describe(self) -> dict[str, object]:
        """Machine-readable description for provenance records."""
        return {
            "unicode_form": self.unicode_form,
            "zwnj": self.zwnj.value,
            "n_selective_rules": len(self.selective_rules),
        }


@dataclass(frozen=True)
class ProcessedWord:
    """One orthographic word after normalization.

    ``pieces`` are the pre-token strings handed to a tokenizer (more than one only
    under ``boundary_marker``). ``to_stripped`` maps every position of the
    concatenated processed string (0..len) to the stripped coordinate space.
    """

    raw: str
    canonical: str
    pieces: tuple[str, ...]
    to_stripped: tuple[int, ...]
    forced_boundaries: tuple[int, ...]

    @property
    def processed(self) -> str:
        """Concatenation of pre-token pieces."""
        return "".join(self.pieces)


def unicode_normalize(text: str, form: str) -> str:
    """Apply ``none``/``NFC``/``NFKC``/``NFD``/``NFKD``."""
    if form.lower() == "none":
        return text
    if form not in {"NFC", "NFKC", "NFD", "NFKD"}:
        raise ValueError(f"unknown unicode form {form!r}")
    return unicodedata.normalize(form, text)  # type: ignore[arg-type]


def strip_format(word: str, chars: frozenset[str] = EVAL_FORMAT_CHARS) -> tuple[str, list[int]]:
    """Remove format characters; return stripped word and a map canonical-pos -> stripped-pos."""
    out: list[str] = []
    mapping: list[int] = []
    for ch in word:
        mapping.append(len(out))
        if ch not in chars:
            out.append(ch)
    mapping.append(len(out))
    return "".join(out), mapping


def process_word(raw: str, policy: NormalizationPolicy) -> ProcessedWord:
    """Normalize one raw orthographic word according to ``policy``."""
    canonical = unicode_normalize(raw, policy.unicode_form)
    _, canon_to_stripped = strip_format(canonical)
    if policy.zwnj is ZwnjPolicy.SELECTIVE and not policy.selective_rules:
        warnings.warn(
            "selective ZWNJ policy has no approved rules; behaving as 'preserve'",
            stacklevel=2,
        )
    kept: list[str] = []
    to_stripped: list[int] = []
    forced: list[int] = []
    for idx, ch in enumerate(canonical):
        action = "keep"
        if ch == ZWNJ:
            if policy.zwnj is ZwnjPolicy.REMOVE:
                action = "remove"
            elif policy.zwnj is ZwnjPolicy.BOUNDARY_MARKER:
                action = "boundary"
            elif policy.zwnj is ZwnjPolicy.SELECTIVE:
                left = canonical[idx - 1] if idx > 0 else ""
                right = canonical[idx + 1] if idx + 1 < len(canonical) else ""
                for rule in policy.selective_rules:
                    if rule.matches(left, right):
                        action = rule.action
                        break
        if action == "keep":
            to_stripped.append(canon_to_stripped[idx])
            kept.append(ch)
        elif action == "boundary" and 0 < len(kept) and idx < len(canonical) - 1:
            if not forced or forced[-1] != len(kept):
                forced.append(len(kept))
    to_stripped.append(canon_to_stripped[len(canonical)])
    processed = "".join(kept)
    pieces: list[str] = []
    prev = 0
    for b in forced:
        if 0 < b < len(processed):
            pieces.append(processed[prev:b])
            prev = b
    pieces.append(processed[prev:])
    pieces = [p for p in pieces if p]
    return ProcessedWord(
        raw=raw,
        canonical=canonical,
        pieces=tuple(pieces) if pieces else ("",),
        to_stripped=tuple(to_stripped),
        forced_boundaries=tuple(b for b in forced if 0 < b < len(processed)),
    )


def tokens_to_stripped_boundaries(pw: ProcessedWord, tokens: list[str]) -> set[int]:
    """Interior boundaries of a tokenization, mapped to the stripped coordinate space.

    Boundaries that collapse to stripped position 0 or to the stripped length are
    dropped (they are word edges in stripped space).
    """
    stripped_len = pw.to_stripped[-1]
    out: set[int] = set()
    pos = 0
    for t in tokens[:-1]:
        pos += len(t)
        s = pw.to_stripped[pos]
        if 0 < s < stripped_len:
            out.add(s)
    return out


def split_words(line: str) -> list[str]:
    """Orthographic words = whitespace-delimited tokens of the raw line.

    TODO(linguistics): script-specific punctuation handling for Sindhi/Urdu is
    unresolved; punctuation currently stays attached to words for every policy.
    """
    return line.split()
