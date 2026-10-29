"""Tokenization-efficiency metrics with explicit denominators.

Denominators (identical across normalization policies by construction):

* **orthographic words**: whitespace-delimited tokens of the *raw* line;
* **characters**: characters of the canonical words *excluding* whitespace and the
  evaluation format characters (ZWNJ, ZWJ), i.e. the length in stripped coordinates.

A lower fertility is **not** by itself evidence of a better tokenizer: it can come
from longer tokens, memorised frequent words, or deleting characters (e.g. removing
ZWNJ deletes tokens a ``preserve`` tokenizer must emit).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from morphtok.data.normalize import ProcessedWord


@dataclass(frozen=True)
class UnitCounts:
    """Counts for one evaluation unit (a line)."""

    tokens: int
    words: int
    chars: int


def unit_counts(encoded_line: Sequence[tuple[ProcessedWord, list[str]]]) -> UnitCounts:
    """Counts for one encoded line (output of ``TokenizationPipeline.encode_line``)."""
    tokens = sum(len(t) for _, t in encoded_line)
    chars = sum(pw.to_stripped[-1] for pw, _ in encoded_line)
    return UnitCounts(tokens=tokens, words=len(encoded_line), chars=chars)


def fertility(units: Iterable[UnitCounts]) -> float | None:
    """Tokens per orthographic word (ratio of sums); ``None`` if there are no words."""
    ulist = list(units)
    words = sum(u.words for u in ulist)
    return sum(u.tokens for u in ulist) / words if words else None


def tokens_per_char(units: Iterable[UnitCounts]) -> float | None:
    """Tokens per stripped character (ratio of sums); ``None`` if there are no chars."""
    ulist = list(units)
    chars = sum(u.chars for u in ulist)
    return sum(u.tokens for u in ulist) / chars if chars else None


def vocab_mismatches(vocab_sizes: Mapping[str, int], target: int, tolerance: int = 0) -> dict[str, int]:
    """Systems whose realised vocabulary differs from ``target`` by more than ``tolerance``.

    Character-level controls should be excluded by the caller (their vocabulary is the
    inventory, not a choice).
    """
    return {k: v for k, v in vocab_sizes.items() if abs(v - target) > tolerance}
