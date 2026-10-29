"""Normalization + (optional) analyzer supervision + tokenizer, as one reproducible unit.

Added beyond the required tree because every experiment family needs the same
composition, and duplicating it in each script would let conditions drift apart.

Known approximation: a training pre-token string can arise from several orthographic
words (e.g. under ``boundary_marker``); its training-time constraints are taken from
the *most frequent* source word. This is recorded in ``stats['constraint_conflicts']``.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field

from morphtok.analyzers.base import Analysis, Analyzer, AnalyzerNotConfiguredError
from morphtok.analyzers.confidence import SupervisionConfig, constraints_for_word
from morphtok.data.normalize import (
    NormalizationPolicy,
    ProcessedWord,
    process_word,
    split_words,
    strip_format,
)
from morphtok.tokenizers.baselines import BaseTokenizer
from morphtok.tokenizers.constraints import WordConstraints


@dataclass
class TokenizationPipeline:
    """Composable condition: policy x tokenizer x analyzer x supervision."""

    policy: NormalizationPolicy
    tokenizer: BaseTokenizer
    analyzer: Analyzer | None = None
    supervision: SupervisionConfig = field(default_factory=SupervisionConfig)
    stats: Counter[str] = field(default_factory=Counter)
    _analysis_cache: dict[str, list[Analysis]] = field(default_factory=dict)
    _word_cache: dict[str, ProcessedWord] = field(default_factory=dict)

    def process(self, raw_word: str) -> ProcessedWord:
        """Normalize one orthographic word (cached)."""
        pw = self._word_cache.get(raw_word)
        if pw is None:
            pw = process_word(raw_word, self.policy)
            self._word_cache[raw_word] = pw
        return pw

    def analyses(self, pw: ProcessedWord) -> list[Analysis]:
        """Analyzer output for the stripped canonical word (cached; failures counted)."""
        if self.analyzer is None:
            return []
        stripped, _ = strip_format(pw.canonical)
        if stripped not in self._analysis_cache:
            try:
                self._analysis_cache[stripped] = self.analyzer.analyze(stripped)
            except AnalyzerNotConfiguredError:
                self.stats["analyzer_not_configured"] += 1
                self._analysis_cache[stripped] = []
        return self._analysis_cache[stripped]

    def constraints(self, pw: ProcessedWord) -> list[WordConstraints | None]:
        """Per-piece constraints (``None`` where there is no evidence)."""
        return constraints_for_word(pw, self.analyses(pw), self.supervision)

    def train(self, lines: Iterable[str]) -> None:
        """Count pre-tokens, attach constraints, fit the tokenizer."""
        counts: Counter[str] = Counter()
        source: dict[str, Counter[tuple[int, ...]]] = {}
        cons_by_key: dict[tuple[str, tuple[int, ...]], WordConstraints | None] = {}
        for line in lines:
            for raw in split_words(line):
                pw = self.process(raw)
                pieces_cons = self.constraints(pw) if self.analyzer else [None] * len(pw.pieces)
                for piece, wc in zip(pw.pieces, pieces_cons, strict=True):
                    if not piece:
                        continue
                    counts[piece] += 1
                    sig = tuple(sorted(wc.constraints)) if wc else ()
                    source.setdefault(piece, Counter())[sig] += 1
                    cons_by_key.setdefault((piece, sig), wc)
        provider_map: dict[str, WordConstraints | None] = {}
        for piece, sigs in source.items():
            if len(sigs) > 1:
                self.stats["constraint_conflicts"] += 1
            best = min(sigs, key=lambda s: (-sigs[s], s))
            provider_map[piece] = cons_by_key[(piece, best)]
        self.tokenizer.train(counts, constraint_provider=provider_map.get)

    def encode_word(self, raw_word: str) -> tuple[ProcessedWord, list[str]]:
        """Tokens for one orthographic word (concatenated over pre-token pieces)."""
        pw = self.process(raw_word)
        pieces_cons = self.constraints(pw) if self.analyzer else [None] * len(pw.pieces)
        tokens: list[str] = []
        for piece, wc in zip(pw.pieces, pieces_cons, strict=True):
            tokens.extend(self.tokenizer.encode_word(piece, wc))
        return pw, tokens

    def encode_line(self, line: str) -> list[tuple[ProcessedWord, list[str]]]:
        """Tokenize every orthographic word of a raw line."""
        return [self.encode_word(w) for w in split_words(line)]
