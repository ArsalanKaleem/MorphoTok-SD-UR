"""sindhinorm: corpus-guided, native-validated spelling normalization for Sindhi.

>>> from sindhinorm import normalize
>>> normalize("هي ڪتاب آهی")  # Farsi yeh in the last word
'هي ڪتاب آهي'
"""

from __future__ import annotations

from functools import lru_cache

from .core import (
    CLASSES,
    KEYBOARD_FOLD,
    LEXICAL,
    MEMBERS,
    NATIVE_KEEP,
    NON_SINDHI,
    SAFE_OOV,
    Normalizer,
    build_lexicon,
    clean_zero_width,
    tokens,
)

__version__ = "0.2.0"
__all__ = [
    "CLASSES", "KEYBOARD_FOLD", "LEXICAL", "MEMBERS", "NATIVE_KEEP", "NON_SINDHI", "SAFE_OOV", "Normalizer", "build_lexicon",
    "clean_zero_width", "default_normalizer", "explain", "normalize", "tokens",
]  # fmt: skip


@lru_cache(maxsize=1)
def default_normalizer() -> Normalizer:
    """The shared normalizer with the bundled lexicon (loaded once)."""
    return Normalizer.default()


def normalize(text: str) -> str:
    """Normalize Sindhi text with the bundled lexicon."""
    return default_normalizer().normalize(text)


def explain(text: str) -> list[dict]:
    """Per-word decisions for ``text`` with the bundled lexicon."""
    return default_normalizer().explain(text)
