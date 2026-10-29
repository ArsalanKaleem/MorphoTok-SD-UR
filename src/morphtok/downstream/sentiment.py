"""Sentiment-classification interface (Gate 5 only; currently a stub).

No Sindhi or Urdu sentiment dataset has been selected or verified. This module only
fixes the interface and the controls every comparison must hold constant.

TODO(resource): choose a dataset; verify its licence, label scheme, split
definitions and known label noise from the primary source before use.
TODO(engineering): implement a small classifier within the single-T4 budget.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DownstreamControls:
    """Everything that must be identical across tokenizers in a downstream comparison."""

    training_data_id: str
    train_steps: int
    vocab_size: int
    max_seq_len: int
    sequence_policy: str  # "truncate_tokens" or "truncate_chars" (must be stated)
    architecture: str
    optimizer: dict[str, float]
    seeds: tuple[int, ...]
    eval_protocol: str
    leakage_check: str


@dataclass
class SentimentTask:
    """Interface for a sentiment benchmark."""

    dataset_id: str | None = None
    labels: list[str] = field(default_factory=list)

    def load(self) -> None:
        """Load the dataset."""
        raise NotImplementedError("no verified sentiment dataset configured")

    def run(self, tokenizer_name: str, controls: DownstreamControls) -> dict[str, float]:
        """Train and evaluate; returns metrics."""
        raise NotImplementedError(
            f"sentiment run for {tokenizer_name} not implemented (Gate 5 has not been reached)"
        )
