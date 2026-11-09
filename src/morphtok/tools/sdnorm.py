"""Sindhi spelling normalizer: re-export of the ``sindhinorm`` package (``packages/sindhinorm``).

The code lives in ``packages/sindhinorm/src/sindhinorm/core.py`` (published on PyPI as
``sindhinorm``); this module keeps the project's older import path working. If the package is
not installed (``pip install -e packages/sindhinorm``), it is imported from the source tree.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from sindhinorm.core import (
        CLASSES,
        LEXICAL,
        MAX_CANDIDATES,
        MEMBERS,
        NATIVE_KEEP,
        SAFE_OOV,
        ZWJ,
        ZWNJ,
        Normalizer,
        build_lexicon,
        clean_zero_width,
        is_word_char,
        tokens,
    )
except ImportError:  # pragma: no cover - source-tree fallback
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "packages" / "sindhinorm" / "src"))
    from sindhinorm.core import (
        CLASSES,
        LEXICAL,
        MAX_CANDIDATES,
        MEMBERS,
        NATIVE_KEEP,
        SAFE_OOV,
        ZWJ,
        ZWNJ,
        Normalizer,
        build_lexicon,
        clean_zero_width,
        is_word_char,
        tokens,
    )

__all__ = [
    "CLASSES", "LEXICAL", "MAX_CANDIDATES", "MEMBERS", "NATIVE_KEEP", "SAFE_OOV", "ZWJ", "ZWNJ",
    "Normalizer", "build_lexicon", "clean_zero_width", "is_word_char", "tokens",
]  # fmt: skip
