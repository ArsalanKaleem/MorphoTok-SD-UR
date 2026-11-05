"""Tagger models: shapes, parameter matching, padding invariance, ability to fit."""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from morphtok.models.tagger import Tagger, Vocab, make_batch, n_parameters  # noqa: E402

SENTS = [
    {"tokens": ["abc", "de", "abcx"], "upos": ["NOUN", "ADP", "NOUN"]},
    {"tokens": ["de", "fgh"], "upos": ["ADP", "VERB"]},
    {"tokens": ["fghy", "abc"], "upos": ["VERB", "NOUN"]},
]


def segment(w: str) -> list[str]:
    return [w[:2], w[2:]] if len(w) > 2 else [w]


def vocabs() -> tuple[Vocab, Vocab, Vocab, Vocab]:
    words = Vocab([t for s in SENTS for t in s["tokens"]])
    chars = Vocab([c for s in SENTS for t in s["tokens"] for c in t])
    pieces = Vocab([p for s in SENTS for t in s["tokens"] for p in segment(t)])
    tags = Vocab([u for s in SENTS for u in s["upos"]])
    return words, chars, pieces, tags


def build(kind: str) -> tuple[Tagger, object]:
    w, c, p, t = vocabs()
    model = Tagger(kind, len(t), len(w), len(c), len(p), dim=16, hidden=16, dropout=0.0)
    return model, make_batch(SENTS, w, c, p, t, segment)


def test_vocab_reserves_pad_and_unk() -> None:
    v = Vocab(["b", "a", "a"])
    assert v.itos[:2] == ["<pad>", "<unk>"] and v("zzz") == 1 and len(v) == 4


@pytest.mark.parametrize("kind", Tagger.KINDS)
def test_forward_backward_shapes(kind: str) -> None:
    torch.manual_seed(0)
    model, b = build(kind)
    logits = model(b)
    n = model.out.out_features
    assert logits.shape == (3, 3, n)
    loss = torch.nn.functional.cross_entropy(
        logits.view(-1, model.out.out_features), b.tags.view(-1), ignore_index=-100
    )
    loss.backward()
    assert all(p.grad is not None for p in model.parameters() if p.requires_grad)


def test_concat_and_gated_are_parameter_matched() -> None:
    assert n_parameters(build("concat")[0]) == n_parameters(build("gated")[0])


def test_padding_does_not_change_predictions() -> None:
    torch.manual_seed(0)
    model, _ = build("gated")
    model.eval()
    w, c, p, t = vocabs()
    alone = model(make_batch([SENTS[1]], w, c, p, t, segment))[0, :2]
    padded = model(make_batch([SENTS[0], SENTS[1]], w, c, p, t, segment))[1, :2]
    assert torch.allclose(alone, padded, atol=1e-5)


def test_gate_mean_is_recorded() -> None:
    model, b = build("gated")
    model(b)
    assert model.last_gate_mean is not None and 0.0 < model.last_gate_mean < 1.0


@pytest.mark.parametrize("kind", Tagger.KINDS)
def test_can_overfit_tiny_data(kind: str) -> None:
    torch.manual_seed(0)
    model, b = build(kind)
    opt = torch.optim.Adam(model.parameters(), lr=0.01)
    for _ in range(100):
        opt.zero_grad()
        logits = model(b)
        torch.nn.functional.cross_entropy(
            logits.view(-1, model.out.out_features), b.tags.view(-1), ignore_index=-100
        ).backward()
        opt.step()
    pred = model(b).argmax(-1)
    mask = b.tags != -100
    assert bool((pred[mask] == b.tags[mask]).all())


def test_unknown_kind_rejected() -> None:
    with pytest.raises(ValueError):
        Tagger("bogus", 2, 2, 2, 2)
