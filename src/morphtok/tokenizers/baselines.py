"""Baseline tokenizers sharing one interface: BPE, Unigram (reference lattice), characters.

All implementations here are pure Python and deterministic given their input. They
are meant for transparent, small-scale experiments; for production-scale corpora a
verified library backend should be added.

TODO(engineering): add optional SentencePiece / HF ``tokenizers`` backends for real
corpora and verify, on a shared corpus, that they agree with these references at
matched vocabulary sizes before mixing results from both.
"""

from __future__ import annotations

import heapq
import itertools
import json
from abc import ABC, abstractmethod
from collections import Counter
from collections.abc import Mapping
from typing import Any

from morphtok import __version__
from morphtok.tokenizers.constraints import ConstraintMode, WordConstraints
from morphtok.tokenizers.lattice_unigram import (
    ConstraintProvider,
    TrainingLog,
    UnigramModel,
    UnigramTrainer,
)


class BaseTokenizer(ABC):
    """Word-level tokenizer: never produces tokens that cross pre-token boundaries."""

    name: str = "base"

    @property
    def version(self) -> str:
        """Implementation identifier recorded in provenance."""
        return f"morphtok-{self.name}-{__version__}"

    @abstractmethod
    def train(
        self, word_counts: Mapping[str, int], constraint_provider: ConstraintProvider | None = None
    ) -> None:
        """Fit the tokenizer to pre-token frequency counts."""

    @abstractmethod
    def encode_word(self, word: str, constraints: WordConstraints | None = None) -> list[str]:
        """Segment one pre-token."""

    @property
    @abstractmethod
    def vocab_size(self) -> int:
        """Size of the learned vocabulary."""

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """JSON-serialisable state."""

    def save(self, path: str) -> None:
        """Write state as JSON."""
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, ensure_ascii=False, indent=1)


class CharTokenizer(BaseTokenizer):
    """Character-level control: every character is a token."""

    name = "char"

    def __init__(self) -> None:
        self.chars: set[str] = set()

    def train(
        self, word_counts: Mapping[str, int], constraint_provider: ConstraintProvider | None = None
    ) -> None:
        """Record the character inventory (used only for ``vocab_size``)."""
        del constraint_provider
        self.chars = {c for w in word_counts for c in w}

    def encode_word(self, word: str, constraints: WordConstraints | None = None) -> list[str]:
        """Split into characters."""
        del constraints
        return list(word)

    @property
    def vocab_size(self) -> int:
        """Character inventory size."""
        return len(self.chars)

    def to_dict(self) -> dict[str, Any]:
        """Serialisable state."""
        return {"type": self.name, "chars": sorted(self.chars)}


class BPETokenizer(BaseTokenizer):
    """Classic word-internal BPE; vocabulary = characters + merges, matched exactly.

    Ties between equally frequent pairs are broken lexicographically, so training is
    deterministic.
    """

    name = "bpe"

    def __init__(self, vocab_size: int) -> None:
        self.target = vocab_size
        self.chars: list[str] = []
        self.merges: list[tuple[str, str]] = []
        self.warnings: list[str] = []

    def train(
        self, word_counts: Mapping[str, int], constraint_provider: ConstraintProvider | None = None
    ) -> None:
        """Learn merges until ``chars + merges == vocab_size`` or no pairs remain."""
        del constraint_provider
        self.chars = sorted({c for w in word_counts for c in w})
        if len(self.chars) > self.target:
            raise ValueError(f"vocab_size={self.target} smaller than character inventory ({len(self.chars)})")
        # Incremental pair counts with a lazy max-heap keyed by (-count, pair): selects
        # exactly the pair the naive recount would (most frequent, then lexicographically
        # smallest); ``_reference_merges`` is the naive version kept for equivalence tests.
        words: list[tuple[str, ...]] = []
        freqs: list[int] = []
        for w, f in word_counts.items():
            if w:
                words.append(tuple(w))
                freqs.append(f)
        pairs: Counter[tuple[str, str]] = Counter()
        where: dict[tuple[str, str], set[int]] = {}
        for idx, sym in enumerate(words):
            for p in itertools.pairwise(sym):
                pairs[p] += freqs[idx]
                where.setdefault(p, set()).add(idx)
        heap = [(-c, p) for p, c in pairs.items()]
        heapq.heapify(heap)
        vocab_len = len(self.chars)
        seen_symbols = set(self.chars)
        while vocab_len < self.target:
            best = None
            while heap:
                neg, p = heapq.heappop(heap)
                if pairs.get(p, 0) == -neg and -neg > 0:
                    best = p
                    break
            if best is None:
                self.warnings.append(f"no more pairs at vocab {vocab_len}; target {self.target} NOT matched")
                break
            self.merges.append(best)
            merged = best[0] + best[1]
            if merged not in seen_symbols:
                seen_symbols.add(merged)
                vocab_len += 1
            changed: set[tuple[str, str]] = set()
            for idx in list(where.get(best, ())):
                old = words[idx]
                new = _apply_merge(old, best)
                if new == old:
                    continue
                f = freqs[idx]
                for p in itertools.pairwise(old):
                    pairs[p] -= f
                    changed.add(p)
                for p in itertools.pairwise(new):
                    pairs[p] += f
                    where.setdefault(p, set()).add(idx)
                    changed.add(p)
                words[idx] = new
            where.pop(best, None)
            for p in changed:
                if pairs[p] > 0:
                    heapq.heappush(heap, (-pairs[p], p))
                else:
                    pairs.pop(p, None)
        self._ranks = {m: r for r, m in enumerate(self.merges)}
        self._symbols = seen_symbols

    def encode_word(self, word: str, constraints: WordConstraints | None = None) -> list[str]:
        """Apply merges in rank order (constraints are ignored by BPE)."""
        del constraints
        sym: tuple[str, ...] = tuple(word)
        ranks = self._ranks
        while len(sym) > 1:
            cands = [(ranks.get((a, b)), i) for i, (a, b) in enumerate(itertools.pairwise(sym))]
            cands = [(r, i) for r, i in cands if r is not None]
            if not cands:
                break
            best_rank = min(r for r, _ in cands)
            sym = _apply_merge(sym, self.merges[best_rank])
        return list(sym)

    @property
    def vocab_size(self) -> int:
        """Number of distinct symbols (characters + merge products)."""
        return len(getattr(self, "_symbols", self.chars))

    def to_dict(self) -> dict[str, Any]:
        """Serialisable state."""
        return {"type": self.name, "chars": self.chars, "merges": [list(m) for m in self.merges]}


def _reference_merges(word_counts: Mapping[str, int], n_merges: int) -> list[tuple[str, str]]:
    """Naive BPE (full pair recount per merge); test oracle for ``BPETokenizer.train``."""
    corpus: Counter[tuple[str, ...]] = Counter()
    for w, f in word_counts.items():
        if w:
            corpus[tuple(w)] += f
    merges: list[tuple[str, str]] = []
    for _ in range(n_merges):
        pairs: Counter[tuple[str, str]] = Counter()
        for sym, f in corpus.items():
            for p in itertools.pairwise(sym):
                pairs[p] += f
        if not pairs:
            break
        best = min(pairs, key=lambda p: (-pairs[p], p))
        merges.append(best)
        new_corpus: Counter[tuple[str, ...]] = Counter()
        for sym, f in corpus.items():
            new_corpus[_apply_merge(sym, best)] += f
        corpus = new_corpus
    return merges


def _apply_merge(sym: tuple[str, ...], pair: tuple[str, str]) -> tuple[str, ...]:
    out: list[str] = []
    i = 0
    while i < len(sym):
        if i + 1 < len(sym) and sym[i] == pair[0] and sym[i + 1] == pair[1]:
            out.append(pair[0] + pair[1])
            i += 2
        else:
            out.append(sym[i])
            i += 1
    return tuple(out)


class UnigramTokenizer(BaseTokenizer):
    """Unigram LM tokenizer on the reference lattice, with optional constraints.

    ``train_mode``/``decode_mode`` choose where constraints act (none/soft/hard);
    ``lam`` is the soft-penalty scale in nats per unit penalty.
    """

    name = "unigram"

    def __init__(
        self,
        vocab_size: int,
        max_piece_len: int = 8,
        train_mode: ConstraintMode = ConstraintMode.NONE,
        decode_mode: ConstraintMode = ConstraintMode.NONE,
        lam: float = 0.0,
        hard_fallback: str = "unconstrained",
        trainer_kwargs: Mapping[str, Any] | None = None,
    ) -> None:
        self.target = vocab_size
        self.max_piece_len = max_piece_len
        self.train_mode = train_mode
        self.decode_mode = decode_mode
        self.lam = lam
        self.hard_fallback = hard_fallback
        self.trainer_kwargs = dict(trainer_kwargs or {})
        self.model: UnigramModel | None = None
        self.training_log: TrainingLog | None = None
        self.decode_fallbacks = 0

    def train(
        self, word_counts: Mapping[str, int], constraint_provider: ConstraintProvider | None = None
    ) -> None:
        """EM training; constraints used in the E-step only if ``train_mode != none``."""
        use = constraint_provider if self.train_mode is not ConstraintMode.NONE else None
        trainer = UnigramTrainer(
            vocab_size=self.target,
            max_piece_len=self.max_piece_len,
            constraint_provider=use,
            lam=self.lam,
            mode=self.train_mode,
            **self.trainer_kwargs,
        )
        self.model = trainer.train(word_counts)
        self.training_log = trainer.log

    def encode_word(self, word: str, constraints: WordConstraints | None = None) -> list[str]:
        """Viterbi decoding, constrained according to ``decode_mode``."""
        if self.model is None:
            raise RuntimeError("tokenizer not trained")
        if not word:
            return []
        mode = self.decode_mode if constraints is not None else ConstraintMode.NONE
        if mode is ConstraintMode.HARD:
            lat = self.model.lattice(word, constraints, self.lam, mode)
            if lat.forward()[len(word)] == float("-inf"):
                self.decode_fallbacks += 1
        return self.model.encode(word, constraints, self.lam, mode, fallback=self.hard_fallback)

    @property
    def vocab_size(self) -> int:
        """Number of pieces."""
        return self.model.vocab_size if self.model else 0

    def to_dict(self) -> dict[str, Any]:
        """Serialisable state."""
        return {
            "type": self.name,
            "train_mode": self.train_mode.value,
            "decode_mode": self.decode_mode.value,
            "lam": self.lam,
            "max_piece_len": self.max_piece_len,
            "hard_fallback": self.hard_fallback,
            "logp": self.model.logp if self.model else {},
        }


def tokenizer_from_dict(d: Mapping[str, Any]) -> BaseTokenizer:
    """Inverse of ``to_dict`` for every tokenizer type."""
    kind = d["type"]
    if kind == "char":
        c = CharTokenizer()
        c.chars = set(d["chars"])
        return c
    if kind == "bpe":
        b = BPETokenizer(vocab_size=len(d["chars"]) + len(d["merges"]))
        b.chars = list(d["chars"])
        b.merges = [(m[0], m[1]) for m in d["merges"]]
        b._ranks = {m: r for r, m in enumerate(b.merges)}
        b._symbols = set(b.chars) | {a + c for a, c in b.merges}
        b.target = len(b._symbols)
        return b
    if kind == "unigram":
        u = UnigramTokenizer(
            vocab_size=len(d["logp"]),
            max_piece_len=int(d["max_piece_len"]),
            train_mode=ConstraintMode(d["train_mode"]),
            decode_mode=ConstraintMode(d["decode_mode"]),
            lam=float(d["lam"]),
            hard_fallback=str(d["hard_fallback"]),
        )
        u.model = UnigramModel(dict(d["logp"]), u.max_piece_len)
        return u
    raise ValueError(f"unknown tokenizer type {kind!r}")


def build_tokenizer(spec: Mapping[str, Any], vocab_size: int) -> BaseTokenizer:
    """Instantiate a tokenizer from a ``configs/tokenizer/*.yaml`` mapping."""
    kind = spec["type"]
    if kind == "bpe":
        return BPETokenizer(vocab_size)
    if kind == "char":
        return CharTokenizer()
    if kind == "unigram":
        return UnigramTokenizer(
            vocab_size,
            max_piece_len=int(spec.get("max_piece_len", 8)),
            train_mode=ConstraintMode(spec.get("train_mode", "none")),
            decode_mode=ConstraintMode(spec.get("decode_mode", "none")),
            lam=float(spec.get("lambda", 0.0)),
            hard_fallback=str(spec.get("hard_fallback", "unconstrained")),
            trainer_kwargs=spec.get("trainer", {}),
        )
    raise ValueError(f"unknown tokenizer type {kind!r}")
