"""Transparent pure-Python reference implementation of a Unigram segmentation lattice.

This is a *reference implementation*, not a claimed contribution. The penalised
distribution below is the standard Unigram LM posterior (Kudo-style) with an added,
explicitly documented per-edge cost; whether that combination is known in the
literature is an open item in ``docs/novelty_screening.md``.

Definitions (see ``docs/lattice.md`` for the long form)
-------------------------------------------------------
For word ``w`` with candidate edges ``e = [i, j)`` whose piece ``w[i:j]`` is in the
vocabulary:

* **per-edge score**     ``phi(e) = log p(e) - lambda * c(e)`` where ``c(e)`` is the
  constraint cost from :meth:`WordConstraints.edge_cost` (``V(s) = sum_e c(e)``).
* **segmentation posterior** ``P(s | w) = exp(alpha * sum_{e in s} phi(e)) / Z``.
  ``alpha`` is an inverse temperature (``alpha = 1`` is the model posterior).
* **partition function** ``Z = sum_{s in S_valid(w)} exp(alpha * sum phi)`` where
  ``S_valid`` is every path through the lattice; hard constraints *remove edges*,
  which is the only place a weight is ``-inf``.
* **training objective** (EM): maximise ``sum_w f(w) log sum_s exp(sum_e phi(e))``
  over ``log p`` with ``lambda`` and constraints fixed (``alpha = 1``).
* **decoding objective**: Viterbi ``argmax_s sum_e phi(e)`` (independent of alpha > 0).

Unseen characters at inference get an explicit single-character edge with log
probability ``unk_logp`` (finite) so the lattice is always connected unless hard
constraints disconnect it.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from morphtok.tokenizers.constraints import (
    ConstraintMode,
    InfeasibleConstraintsError,
    WordConstraints,
    boundaries_of,
)

NEG_INF: float = float("-inf")


class NoValidSegmentationError(ValueError):
    """Raised when the lattice for a word has no complete path."""


def logsumexp(values: list[float]) -> float:
    """Numerically stable ``log(sum(exp(v)))``; returns ``-inf`` for empty/all ``-inf``."""
    if not values:
        return NEG_INF
    m = max(values)
    if m == NEG_INF:
        return NEG_INF
    return m + math.log(sum(math.exp(v - m) for v in values))


@dataclass(frozen=True)
class Edge:
    """One candidate piece ``word[start:end]`` with its log-probability and cost."""

    start: int
    end: int
    piece: str
    logp: float
    cost: float

    def score(self, lam: float) -> float:
        """Per-edge score ``log p(e) - lambda * c(e)``."""
        return self.logp - lam * self.cost


@dataclass
class Lattice:
    """All candidate edges of one word plus DP tables (computed lazily)."""

    word: str
    edges_by_end: list[list[Edge]]
    lam: float = 0.0
    alpha: float = 1.0
    _fwd: list[float] | None = field(default=None, repr=False)
    _bwd: list[float] | None = field(default=None, repr=False)

    @property
    def n(self) -> int:
        """Word length in characters."""
        return len(self.word)

    def weight(self, e: Edge) -> float:
        """Log weight of an edge under the sampling distribution: ``alpha * phi(e)``."""
        return self.alpha * e.score(self.lam)

    def forward(self) -> list[float]:
        """``fwd[j] = log`` total weight of all partial paths from 0 to ``j``."""
        if self._fwd is None:
            fwd = [NEG_INF] * (self.n + 1)
            fwd[0] = 0.0
            for j in range(1, self.n + 1):
                fwd[j] = logsumexp([fwd[e.start] + self.weight(e) for e in self.edges_by_end[j]])
            self._fwd = fwd
        return self._fwd

    def backward(self) -> list[float]:
        """``bwd[i] = log`` total weight of all partial paths from ``i`` to ``n``."""
        if self._bwd is None:
            n = self.n
            out_edges: list[list[Edge]] = [[] for _ in range(n + 1)]
            for j in range(1, n + 1):
                for e in self.edges_by_end[j]:
                    out_edges[e.start].append(e)
            bwd = [NEG_INF] * (n + 1)
            bwd[n] = 0.0
            for i in range(n - 1, -1, -1):
                bwd[i] = logsumexp([self.weight(e) + bwd[e.end] for e in out_edges[i]])
            self._bwd = bwd
        return self._bwd

    def log_partition(self) -> float:
        """``log Z``; raises if the lattice has no complete path."""
        if self.n == 0:
            return 0.0
        z = self.forward()[self.n]
        if z == NEG_INF:
            raise NoValidSegmentationError(f"no complete path for {self.word!r}")
        return z

    def edge_marginals(self) -> dict[tuple[int, int], float]:
        """Posterior probability that each edge ``(start, end)`` is used."""
        if self.n == 0:
            return {}
        log_z = self.log_partition()
        fwd, bwd = self.forward(), self.backward()
        out: dict[tuple[int, int], float] = {}
        for j in range(1, self.n + 1):
            for e in self.edges_by_end[j]:
                lp = fwd[e.start] + self.weight(e) + bwd[e.end] - log_z
                if lp > NEG_INF:
                    out[(e.start, e.end)] = math.exp(lp)
        return out

    def viterbi(self) -> tuple[list[str], float]:
        """Highest-scoring segmentation and its total score ``sum phi(e)``."""
        if self.n == 0:
            return [], 0.0
        best = [NEG_INF] * (self.n + 1)
        back: list[Edge | None] = [None] * (self.n + 1)
        best[0] = 0.0
        for j in range(1, self.n + 1):
            for e in self.edges_by_end[j]:
                cand = best[e.start] + e.score(self.lam)
                # Deterministic tie-break: prefer the longer piece (smaller start).
                if cand > best[j] or (cand == best[j] and back[j] is not None and e.start < back[j].start):
                    best[j] = cand
                    back[j] = e
        if best[self.n] == NEG_INF:
            raise NoValidSegmentationError(f"no complete path for {self.word!r}")
        pieces: list[str] = []
        j = self.n
        while j > 0:
            e = back[j]
            assert e is not None
            pieces.append(e.piece)
            j = e.start
        return pieces[::-1], best[self.n]

    def sample(self, rng: random.Random) -> list[str]:
        """Forward-filter / backward-sample one segmentation from ``P(s | w)``."""
        if self.n == 0:
            return []
        self.log_partition()  # raises on unreachable
        fwd = self.forward()
        pieces: list[str] = []
        j = self.n
        while j > 0:
            cands = self.edges_by_end[j]
            logits = [fwd[e.start] + self.weight(e) for e in cands]
            norm = logsumexp(logits)
            r = rng.random()
            acc = 0.0
            chosen = cands[-1]
            for e, lg in zip(cands, logits, strict=True):
                acc += math.exp(lg - norm)
                if r < acc:
                    chosen = e
                    break
            pieces.append(chosen.piece)
            j = chosen.start
        return pieces[::-1]

    def nbest(self, k: int) -> list[tuple[list[str], float]]:
        """Exact k-best segmentations by total score (DP keeping top-k per node)."""
        if k < 1:
            raise ValueError("k must be >= 1")
        if self.n == 0:
            return [([], 0.0)]
        table: list[list[tuple[float, tuple[str, ...]]]] = [[] for _ in range(self.n + 1)]
        table[0] = [(0.0, ())]
        for j in range(1, self.n + 1):
            cands: list[tuple[float, tuple[str, ...]]] = []
            for e in self.edges_by_end[j]:
                s = e.score(self.lam)
                for prev_score, prev_path in table[e.start]:
                    cands.append((prev_score + s, (*prev_path, e.piece)))
            cands.sort(key=lambda t: (-t[0], t[1]))
            table[j] = cands[:k]
        if not table[self.n]:
            raise NoValidSegmentationError(f"no complete path for {self.word!r}")
        return [(list(p), s) for s, p in table[self.n]]

    def entropy(self) -> float:
        """Shannon entropy (nats) of ``P(s | w)``; a *diagnostic*, not an objective term.

        ``H = log Z - E[alpha * sum_e phi(e)]`` with the expectation from edge marginals.
        """
        if self.n == 0:
            return 0.0
        log_z = self.log_partition()
        marg = self.edge_marginals()
        expected = 0.0
        for j in range(1, self.n + 1):
            for e in self.edges_by_end[j]:
                m = marg.get((e.start, e.end), 0.0)
                if m > 0.0:
                    expected += m * self.weight(e)
        return max(0.0, log_z - expected)

    def enumerate_all(self, limit: int = 100_000) -> list[tuple[list[str], float]]:
        """Exhaustive enumeration (test oracle only; exponential in word length)."""
        out: list[tuple[list[str], float]] = []

        def rec(j: int, suffix: list[str], score: float) -> None:
            if len(out) >= limit:
                raise RuntimeError("enumeration limit exceeded")
            if j == 0:
                out.append((suffix[::-1], score))
                return
            for e in self.edges_by_end[j]:
                rec(e.start, [*suffix, e.piece], score + e.score(self.lam))

        if self.n == 0:
            return [([], 0.0)]
        rec(self.n, [], 0.0)
        return out


@dataclass
class UnigramModel:
    """A vocabulary of pieces with log-probabilities."""

    logp: dict[str, float]
    max_piece_len: int = 8
    unk_logp: float = -30.0

    def __post_init__(self) -> None:
        for piece, lp in self.logp.items():
            if not piece:
                raise ValueError("empty piece in vocabulary")
            if not math.isfinite(lp):
                raise ValueError(f"non-finite log probability for {piece!r}")
        if not math.isfinite(self.unk_logp):
            raise ValueError("unk_logp must be finite")

    @property
    def vocab_size(self) -> int:
        """Number of pieces (excluding the implicit unknown-character edge)."""
        return len(self.logp)

    def lattice(
        self,
        word: str,
        constraints: WordConstraints | None = None,
        lam: float = 0.0,
        mode: ConstraintMode = ConstraintMode.NONE,
        alpha: float = 1.0,
        exclude: str | None = None,
    ) -> Lattice:
        """Build the candidate-edge lattice for ``word``.

        ``exclude`` removes one piece (used by vocabulary pruning). In HARD mode,
        constraint-violating edges are omitted (the documented ``-inf`` exclusion).
        """
        if alpha <= 0.0:
            raise ValueError("alpha must be > 0")
        if lam < 0.0:
            raise ValueError("lambda must be >= 0")
        n = len(word)
        if constraints is not None and constraints.n != n:
            raise ValueError(f"constraints built for length {constraints.n}, word has {n}")
        use_cost = constraints is not None and mode is ConstraintMode.SOFT
        use_hard = constraints is not None and mode is ConstraintMode.HARD
        edges_by_end: list[list[Edge]] = [[] for _ in range(n + 1)]
        for i in range(n):
            for j in range(i + 1, min(n, i + self.max_piece_len) + 1):
                piece = word[i:j]
                if piece == exclude:
                    continue
                lp = self.logp.get(piece)
                if lp is None:
                    if j == i + 1:
                        lp = self.unk_logp
                    else:
                        continue
                if use_hard and constraints is not None and not constraints.edge_allowed_hard(i, j):
                    continue
                cost = constraints.edge_cost(i, j) if use_cost and constraints is not None else 0.0
                edges_by_end[j].append(Edge(i, j, piece, lp, cost))
        return Lattice(word=word, edges_by_end=edges_by_end, lam=lam if use_cost else 0.0, alpha=alpha)

    def encode(
        self,
        word: str,
        constraints: WordConstraints | None = None,
        lam: float = 0.0,
        mode: ConstraintMode = ConstraintMode.NONE,
        fallback: str = "error",
    ) -> list[str]:
        """Viterbi segmentation.

        ``fallback`` applies only when HARD constraints are infeasible:
        ``"error"`` raises :class:`InfeasibleConstraintsError`; ``"unconstrained"``
        decodes without constraints. Both outcomes are documented; neither silently
        returns an invalid segmentation.
        """
        try:
            pieces, _ = self.lattice(word, constraints, lam, mode).viterbi()
            return pieces
        except NoValidSegmentationError:
            if mode is not ConstraintMode.HARD:
                raise
            if fallback == "unconstrained":
                pieces, _ = self.lattice(word).viterbi()
                return pieces
            raise InfeasibleConstraintsError(
                f"hard constraints leave no valid segmentation for {word!r}"
            ) from None


ConstraintProvider = Callable[[str], WordConstraints | None]


@dataclass
class TrainingLog:
    """Diagnostics recorded by :class:`UnigramTrainer`."""

    rounds: list[dict[str, float]] = field(default_factory=list)
    hard_fallbacks: int = 0
    zero_count_pieces_final: int = 0
    warnings: list[str] = field(default_factory=list)


@dataclass
class UnigramTrainer:
    """Small-corpus EM training with loss-based pruning to an *exact* vocabulary size.

    Algorithm (mathematically consistent with the objective in the module docstring):

    1. Seed vocabulary: every character (never pruned) plus the most frequent
       substrings of length 2..``max_piece_len`` (frequency x length ranking).
    2. Repeat until ``vocab_size`` is reached: ``em_iters`` EM iterations (E-step:
       edge marginals under the optionally constrained lattice; M-step: renormalise
       expected counts with additive smoothing ``smoothing``), then prune: drop the
       pieces whose removal least increases the (approximate) corpus NLL, keeping at
       least ``shrink`` of the current vocabulary per round.
    3. Final EM iterations at the target size.

    Constraints enter the E-step only if ``constraint_provider`` is given; this is the
    "constraints shape the vocabulary" intervention.

    TODO(science): the pruning loss ignores renormalisation and inter-piece effects,
    as SentencePiece's approximation is commonly described; verify against the
    primary source before describing it as equivalent.
    """

    vocab_size: int
    max_piece_len: int = 8
    seed_multiplier: int = 10
    min_seed_freq: int = 2
    em_iters: int = 2
    final_em_iters: int = 2
    shrink: float = 0.75
    smoothing: float = 1e-3
    constraint_provider: ConstraintProvider | None = None
    lam: float = 0.0
    mode: ConstraintMode = ConstraintMode.NONE
    log: TrainingLog = field(default_factory=TrainingLog)

    def _seed(self, word_counts: Mapping[str, int]) -> tuple[set[str], dict[str, float]]:
        chars: Counter[str] = Counter()
        subs: Counter[str] = Counter()
        for w, f in word_counts.items():
            for ch in w:
                chars[ch] += f
            for i in range(len(w)):
                for j in range(i + 2, min(len(w), i + self.max_piece_len) + 1):
                    subs[w[i:j]] += f
        if len(chars) > self.vocab_size:
            raise ValueError(
                f"vocab_size={self.vocab_size} is smaller than the character inventory "
                f"({len(chars)}); character coverage would be lost"
            )
        budget = max(self.vocab_size * self.seed_multiplier, self.vocab_size)
        ranked = sorted(
            (s for s, f in subs.items() if f >= self.min_seed_freq),
            key=lambda s: (-subs[s] * len(s), s),
        )[:budget]
        counts = {**{c: float(f) for c, f in chars.items()}, **{s: float(subs[s]) for s in ranked}}
        total = sum(counts.values())
        return set(chars), {p: math.log(c / total) for p, c in counts.items()}

    def _constraints(self, word: str) -> WordConstraints | None:
        return self.constraint_provider(word) if self.constraint_provider else None

    def _e_step(self, model: UnigramModel, word_counts: Mapping[str, int]) -> tuple[Counter[str], float]:
        expected: Counter[str] = Counter()
        loglik = 0.0
        for w, f in word_counts.items():
            if not w:
                continue
            cons = self._constraints(w)
            lat = model.lattice(w, cons, self.lam, self.mode)
            try:
                log_z = lat.log_partition()
            except NoValidSegmentationError:
                if self.mode is not ConstraintMode.HARD:
                    raise
                self.log.hard_fallbacks += 1
                lat = model.lattice(w)
                log_z = lat.log_partition()
            loglik += f * log_z
            for (i, j), m in lat.edge_marginals().items():
                expected[w[i:j]] += f * m
        return expected, loglik

    def _m_step(self, vocab: set[str], expected: Counter[str]) -> dict[str, float]:
        total = sum(expected[p] for p in vocab) + self.smoothing * len(vocab)
        return {p: math.log((expected[p] + self.smoothing) / total) for p in vocab}

    def _prune_losses(self, model: UnigramModel, expected: Counter[str], chars: set[str]) -> dict[str, float]:
        losses: dict[str, float] = {}
        for piece, lp in model.logp.items():
            if piece in chars:
                continue
            alt, alt_score = model.lattice(piece, exclude=piece).viterbi()
            del alt
            losses[piece] = expected[piece] * (lp - alt_score)
        return losses

    def train(self, word_counts: Mapping[str, int]) -> UnigramModel:
        """Fit a model with exactly ``vocab_size`` pieces (or raise)."""
        if not word_counts:
            raise ValueError("empty training data")
        chars, logp = self._seed(word_counts)
        model = UnigramModel(logp, self.max_piece_len)
        vocab = set(logp)
        round_idx = 0
        while True:
            expected: Counter[str] = Counter()
            ll = 0.0
            for _ in range(self.em_iters):
                expected, ll = self._e_step(model, word_counts)
                model = UnigramModel(self._m_step(vocab, expected), self.max_piece_len)
            self.log.rounds.append({"round": float(round_idx), "vocab": float(len(vocab)), "loglik": ll})
            if len(vocab) <= self.vocab_size:
                break
            losses = self._prune_losses(model, expected, chars)
            keep_n = max(self.vocab_size, int(len(vocab) * self.shrink)) - len(chars)
            kept = sorted(losses, key=lambda p: (-losses[p], p))[:keep_n]
            vocab = chars | set(kept)
            model = UnigramModel({p: model.logp[p] for p in vocab}, self.max_piece_len)
            round_idx += 1
        if len(vocab) < self.vocab_size:
            self.log.warnings.append(
                f"seed vocabulary ({len(vocab)}) smaller than target {self.vocab_size}; "
                "vocabulary size is NOT matched"
            )
        for _ in range(self.final_em_iters):
            expected, _ = self._e_step(model, word_counts)
            model = UnigramModel(self._m_step(vocab, expected), self.max_piece_len)
        self.log.zero_count_pieces_final = sum(1 for p in vocab if expected[p] < 1e-9)
        return model


def segmentation_boundaries(pieces: list[str]) -> list[int]:
    """Re-export of :func:`boundaries_of` for convenience."""
    return boundaries_of(pieces)
