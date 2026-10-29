"""Named-entity-recognition interface (Gate 5 only; currently a stub).

Tokenizer changes alter how word-level entity labels map to subword tokens; the
alignment policy (first-subword vs all-subword labelling) must be fixed in advance
and identical across tokenizers.

TODO(resource): select and verify an NER dataset (licence, tag set, splits).
TODO(science): preregister the label-alignment policy.
"""

from __future__ import annotations

from dataclasses import dataclass

from morphtok.downstream.sentiment import DownstreamControls


@dataclass
class NERTask:
    """Interface for an NER benchmark."""

    dataset_id: str | None = None
    label_alignment: str = "first_subword"

    def align_labels(self, word_labels: list[str], tokens_per_word: list[int]) -> list[str]:
        """Word labels -> subword labels under ``label_alignment`` (implemented, tested logic)."""
        if len(word_labels) != len(tokens_per_word):
            raise ValueError("one token count per word is required")
        out: list[str] = []
        for lab, k in zip(word_labels, tokens_per_word, strict=True):
            if k < 1:
                raise ValueError("every word must have at least one token")
            if self.label_alignment == "first_subword":
                out.extend([lab] + ["IGNORE"] * (k - 1))
            elif self.label_alignment == "all_subwords":
                inside = "I-" + lab[2:] if lab.startswith("B-") else lab
                out.extend([lab] + [inside] * (k - 1))
            else:
                raise ValueError(f"unknown alignment {self.label_alignment!r}")
        return out

    def run(self, tokenizer_name: str, controls: DownstreamControls) -> dict[str, float]:
        """Train and evaluate."""
        raise NotImplementedError(f"NER run for {tokenizer_name} not implemented (Gate 5)")
