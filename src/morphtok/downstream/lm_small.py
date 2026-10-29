"""Small language-model comparisons, normalised per character.

Implemented: a token-bigram LM with add-k smoothing reporting **bits per stripped
character**, a tokenizer-comparable CPU sanity proxy. It is *not* a neural LM and its
results must not be described as language-modelling performance of a Transformer.

Comparisons across tokenizers must use per-character (not per-token) normalisation,
since per-token perplexity rewards tokenizers that produce more, easier tokens.

TODO(engineering): small Transformer LM within one T4 (~16 GB) with identical
architecture, steps, and character-budgeted sequence policy across tokenizers.
"""

from __future__ import annotations

import itertools
import math
from collections import Counter
from collections.abc import Sequence

BOS = "<s>"
EOS = "</s>"


class BigramLM:
    """Add-k smoothed token bigram LM over tokenized lines."""

    def __init__(self, k: float = 0.1) -> None:
        if k <= 0:
            raise ValueError("k must be > 0")
        self.k = k
        self.unigrams: Counter[str] = Counter()
        self.bigrams: Counter[tuple[str, str]] = Counter()
        self.vocab: set[str] = set()

    def fit(self, lines: Sequence[Sequence[str]]) -> None:
        """Count bigrams with sentence boundaries."""
        for toks in lines:
            seq = [BOS, *toks, EOS]
            self.vocab.update(seq)
            for a, b in itertools.pairwise(seq):
                self.unigrams[a] += 1
                self.bigrams[(a, b)] += 1
        self.vocab.add("<unk>")

    def logprob(self, a: str, b: str) -> float:
        """Natural-log ``p(b | a)``; unseen tokens map to ``<unk>``."""
        v = len(self.vocab)
        b = b if b in self.vocab else "<unk>"
        return math.log((self.bigrams[(a, b)] + self.k) / (self.unigrams[a] + self.k * v))

    def bits_per_char(self, lines: Sequence[Sequence[str]], n_chars: int) -> float | None:
        """Total ``-log2 p`` over ``lines`` divided by ``n_chars`` (stripped characters)."""
        if n_chars <= 0:
            return None
        nll = 0.0
        for toks in lines:
            seq = [BOS, *toks, EOS]
            for a, b in itertools.pairwise(seq):
                nll -= self.logprob(a, b)
        return nll / math.log(2) / n_chars
