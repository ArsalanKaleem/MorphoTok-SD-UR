"""Format-character audit: frequency, neighbour classes, word position, runs, joining.

Reports ZWNJ (U+200C), ZWJ (U+200D) and every other ``Cf`` character *separately*;
it never assumes their functions are interchangeable.

Joining classes: Python's :mod:`unicodedata` does not expose Arabic joining types.
If the path to a verified Unicode ``ArabicShaping.txt`` is supplied, it is parsed and
used; otherwise every joining-class output is the string ``"UNAVAILABLE"``.
TODO(resource): pin the Unicode version of ``ArabicShaping.txt`` to the version of
``unicodedata.unidata_version`` used for general categories.

Frequency of a sequence is never treated as evidence that it is morphologically
valid; this module only counts.
"""

from __future__ import annotations

import unicodedata
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from morphtok.data.normalize import ZWJ, ZWNJ, unicode_normalize

UNAVAILABLE = "UNAVAILABLE"


def load_joining_types(path: str | Path | None) -> dict[int, str] | None:
    """Parse ``ArabicShaping.txt`` (``code; name; joining_type; group``) if available."""
    if path is None or not Path(path).exists():
        return None
    out: dict[int, str] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(";")]
        if len(parts) >= 3:
            out[int(parts[0], 16)] = parts[2]
    return out


def char_class(ch: str) -> str:
    """Coarse class of a neighbour: general category plus script-name prefix.

    The script prefix is the first word of the Unicode name (e.g. ``ARABIC``); it is a
    heuristic label for reporting, not a script property lookup.
    """
    if ch == "":
        return "EDGE"
    cat = unicodedata.category(ch)
    name = unicodedata.name(ch, "UNNAMED")
    return f"{cat}:{name.split(' ', 1)[0]}"


def position_in_word(idx: int, word: str) -> str:
    """``initial`` / ``medial`` / ``final`` / ``isolated`` for the character at ``idx``."""
    if len(word) == 1:
        return "isolated"
    if idx == 0:
        return "initial"
    if idx == len(word) - 1:
        return "final"
    return "medial"


@dataclass
class FormatCharStats:
    """Audit statistics for one format character."""

    codepoint: str
    count: int = 0
    words_containing: int = 0
    position: Counter[str] = field(default_factory=Counter)
    left_class: Counter[str] = field(default_factory=Counter)
    right_class: Counter[str] = field(default_factory=Counter)
    left_joining: Counter[str] = field(default_factory=Counter)
    right_joining: Counter[str] = field(default_factory=Counter)
    run_lengths: Counter[int] = field(default_factory=Counter)

    def to_dict(self, top: int = 15) -> dict[str, Any]:
        """JSON-friendly summary (top-``top`` classes)."""
        return {
            "codepoint": self.codepoint,
            "count": self.count,
            "words_containing": self.words_containing,
            "position": dict(self.position),
            "left_class": dict(self.left_class.most_common(top)),
            "right_class": dict(self.right_class.most_common(top)),
            "left_joining": dict(self.left_joining.most_common(top)),
            "right_joining": dict(self.right_joining.most_common(top)),
            "run_lengths": {str(k): v for k, v in sorted(self.run_lengths.items())},
        }


def _joining(ch: str, table: dict[int, str] | None) -> str:
    if table is None:
        return UNAVAILABLE
    if ch == "":
        return "EDGE"
    return table.get(ord(ch), "U(default)")


def audit_lines(
    lines: Iterable[str], unicode_form: str = "NFC", joining_table: dict[int, str] | None = None
) -> dict[str, Any]:
    """Audit format characters in canonical text, and the effect of normalization."""
    stats: dict[str, FormatCharStats] = {}
    n_words = 0
    n_chars = 0
    norm_changed_lines = 0
    n_lines = 0
    for raw_line in lines:
        n_lines += 1
        line = unicode_normalize(raw_line, unicode_form)
        if line != raw_line:
            norm_changed_lines += 1
        for word in line.split():
            n_words += 1
            n_chars += len(word)
            seen_in_word: set[str] = set()
            i = 0
            while i < len(word):
                ch = word[i]
                if unicodedata.category(ch) != "Cf":
                    i += 1
                    continue
                j = i
                while j < len(word) and word[j] == ch:
                    j += 1
                cp = f"U+{ord(ch):04X}"
                st = stats.setdefault(cp, FormatCharStats(codepoint=cp))
                left = word[i - 1] if i > 0 else ""
                right = word[j] if j < len(word) else ""
                st.count += j - i
                st.run_lengths[j - i] += 1
                st.position[position_in_word(i, word)] += 1
                st.left_class[char_class(left)] += 1
                st.right_class[char_class(right)] += 1
                st.left_joining[_joining(left, joining_table)] += 1
                st.right_joining[_joining(right, joining_table)] += 1
                seen_in_word.add(cp)
                i = j
            for cp in seen_in_word:
                stats[cp].words_containing += 1
    return {
        "unicode_form": unicode_form,
        "unicode_version": unicodedata.unidata_version,
        "joining_data": "available" if joining_table is not None else UNAVAILABLE,
        "n_lines": n_lines,
        "n_lines_changed_by_normalization": norm_changed_lines,
        "n_words": n_words,
        "n_chars": n_chars,
        "zwnj_present": f"U+{ord(ZWNJ):04X}" in stats,
        "zwj_present": f"U+{ord(ZWJ):04X}" in stats,
        "format_chars": {cp: s.to_dict() for cp, s in sorted(stats.items())},
    }
