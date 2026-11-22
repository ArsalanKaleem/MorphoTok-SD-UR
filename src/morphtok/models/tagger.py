"""BiLSTM POS taggers that differ only in how a word is represented (combined plan).

Every system shares the same sentence encoder (BiLSTM) and output layer. Word
representations (all ``dim``-dimensional):

* ``word``    embedding of the whole word form (UNK for forms not in the training budget);
* ``char``    character CNN (filter widths 2, 3, 4; max-pooled; projected to ``dim``);
* ``sub``     mean of subword-piece embeddings from an external tokenizer;
* ``concat``  ``Linear([h_sub; h_char])``;
* ``gated``   ``g * h_sub + (1 - g) * h_char``, ``g = sigmoid(Linear([h_sub; h_char]))``.

``concat`` and ``gated`` have the same number of fusion parameters (one 2d -> d linear
map), so a difference between them isolates the gating, not capacity. This is a small,
CPU-scale stand-in for the XLM-R fusion experiment (``notebooks/01_xlmr_fusion_t4.ipynb``).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import torch
from torch import nn

PAD, UNK = "<pad>", "<unk>"


class Vocab:
    """String-to-index map with PAD = 0 and UNK = 1."""

    def __init__(self, items: Sequence[str]) -> None:
        self.itos = [PAD, UNK, *sorted(set(items) - {PAD, UNK})]
        self.stoi = {s: i for i, s in enumerate(self.itos)}

    def __len__(self) -> int:
        return len(self.itos)

    def __call__(self, s: str) -> int:
        """Index of ``s`` (UNK if absent)."""
        return self.stoi.get(s, 1)


@dataclass
class Batch:
    """Padded tensors for one batch of sentences."""

    words: torch.Tensor  # (B, T)
    chars: torch.Tensor  # (B, T, C)
    pieces: torch.Tensor  # (B, T, P)
    tags: torch.Tensor  # (B, T), -100 = padding
    lengths: torch.Tensor  # (B,)


class CharCNN(nn.Module):
    """Character CNN word encoder."""

    def __init__(self, n_chars: int, dim: int, char_dim: int = 32, filters: int = 64) -> None:
        super().__init__()
        self.emb = nn.Embedding(n_chars, char_dim, padding_idx=0)
        self.convs = nn.ModuleList(nn.Conv1d(char_dim, filters, k, padding=k // 2) for k in (2, 3, 4))
        self.proj = nn.Linear(3 * filters, dim)

    def forward(self, chars: torch.Tensor) -> torch.Tensor:
        """(B, T, C) -> (B, T, dim). Only real (non-padding) word slots are convolved."""
        b, t, c = chars.shape
        flat = chars.view(b * t, c)
        real = flat[:, 0] != 0
        words = flat[real]
        x = self.emb(words).transpose(1, 2)
        mask = (words != 0).unsqueeze(1)
        feats = []
        for conv in self.convs:
            h = torch.relu(conv(x))[:, :, :c]
            feats.append(h.masked_fill(~mask, -1e4).max(dim=2).values)
        out = torch.zeros(b * t, self.proj.out_features, dtype=x.dtype, device=x.device)
        out[real] = self.proj(torch.cat(feats, dim=1))
        return out.view(b, t, -1)


class PieceMean(nn.Module):
    """Mean of subword-piece embeddings per word."""

    def __init__(self, n_pieces: int, dim: int) -> None:
        super().__init__()
        self.emb = nn.Embedding(n_pieces, dim, padding_idx=0)

    def forward(self, pieces: torch.Tensor) -> torch.Tensor:
        """(B, T, P) -> (B, T, dim)."""
        mask = (pieces != 0).unsqueeze(-1).float()
        s = (self.emb(pieces) * mask).sum(dim=2)
        return s / mask.sum(dim=2).clamp(min=1.0)


class Tagger(nn.Module):
    """Word encoder (by ``kind``) + BiLSTM + linear tag classifier."""

    KINDS = ("word", "char", "sub", "concat", "gated")

    def __init__(
        self,
        kind: str,
        n_tags: int,
        n_words: int,
        n_chars: int,
        n_pieces: int,
        dim: int = 128,
        hidden: int = 128,
        dropout: float = 0.3,
    ) -> None:
        super().__init__()
        if kind not in self.KINDS:
            raise ValueError(f"unknown kind {kind!r}")
        self.kind = kind
        self.word = nn.Embedding(n_words, dim, padding_idx=0) if kind == "word" else None
        self.char = CharCNN(n_chars, dim) if kind in ("char", "concat", "gated") else None
        self.sub = PieceMean(n_pieces, dim) if kind in ("sub", "concat", "gated") else None
        self.fuse = nn.Linear(2 * dim, dim) if kind in ("concat", "gated") else None
        self.drop = nn.Dropout(dropout)
        self.lstm = nn.LSTM(dim, hidden, batch_first=True, bidirectional=True)
        self.out = nn.Linear(2 * hidden, n_tags)
        self.last_gate_mean: float | None = None

    def represent(self, b: Batch) -> torch.Tensor:
        """Word vectors (B, T, dim) for the configured representation."""
        if self.kind == "word":
            assert self.word is not None
            return self.word(b.words)
        if self.kind == "char":
            assert self.char is not None
            return self.char(b.chars)
        if self.kind == "sub":
            assert self.sub is not None
            return self.sub(b.pieces)
        assert self.sub is not None and self.char is not None and self.fuse is not None
        hs, hc = self.sub(b.pieces), self.char(b.chars)
        z = self.fuse(torch.cat([hs, hc], dim=-1))
        if self.kind == "concat":
            return torch.tanh(z)
        g = torch.sigmoid(z)
        mask = (b.words != 0).unsqueeze(-1).float()
        self.last_gate_mean = float((g.detach() * mask).sum() / (mask.sum() * g.shape[-1]).clamp(min=1.0))
        return g * hs + (1 - g) * hc

    def forward(self, b: Batch) -> torch.Tensor:
        """Tag logits (B, T, n_tags)."""
        x = self.drop(self.represent(b))
        packed = nn.utils.rnn.pack_padded_sequence(x, b.lengths, batch_first=True, enforce_sorted=False)
        h, _ = self.lstm(packed)
        h, _ = nn.utils.rnn.pad_packed_sequence(h, batch_first=True, total_length=x.shape[1])
        return self.out(self.drop(h))


def make_batch(
    sents: Sequence[dict],
    words: Vocab,
    chars: Vocab,
    pieces: Vocab,
    tags: Vocab,
    segment: Callable[[str], list[str]] | None,
    max_chars: int = 16,
    max_pieces: int = 8,
) -> Batch:
    """Pad a list of sentences (dicts with ``tokens`` and ``upos``) into tensors."""
    t_max = max(len(s["tokens"]) for s in sents)
    bsz = len(sents)
    w = torch.zeros(bsz, t_max, dtype=torch.long)
    c = torch.zeros(bsz, t_max, max_chars, dtype=torch.long)
    p = torch.zeros(bsz, t_max, max_pieces, dtype=torch.long)
    y = torch.full((bsz, t_max), -100, dtype=torch.long)
    for i, s in enumerate(sents):
        for j, tok in enumerate(s["tokens"]):
            w[i, j] = words(tok)
            for k, ch in enumerate(tok[:max_chars]):
                c[i, j, k] = chars(ch)
            if segment is not None:
                for k, piece in enumerate(segment(tok)[:max_pieces]):
                    p[i, j, k] = pieces(piece)
            y[i, j] = tags(s["upos"][j]) if "upos" in s else -100
    lengths = torch.tensor([len(s["tokens"]) for s in sents], dtype=torch.long)
    return Batch(w, c, p, y, lengths)


def n_parameters(model: nn.Module) -> int:
    """Trainable parameter count."""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
