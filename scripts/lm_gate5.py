"""Gate 5 (H7): small causal transformer LM per tokenizer; bits per character on held-out text.

Input: the ``.npz`` files from ``scripts/14_export_lm_data.py`` (one per tokenizer × vocab ×
seed). Needs only numpy and torch, so it runs on Kaggle without this repository.

Every model has the same architecture and training recipe; only the tokenizer (and hence
the vocabulary size and the number of tokens per character) differs. Training uses random
windows of the train stream, AdamW with warm-up and cosine decay, early stopping on dev bpc.
Evaluation scores every test token once with overlapping windows (each scored token sees at
least ``ctx/2`` tokens of context, except at the start of the stream).

Reports per run: dev and test bpc; test bpc on words whose lemma was held out from tokenizer
supervision, on words whose form never occurs in the LM training text, and on the rest.
Results are appended to ``<out>/results_lm_<lang>.jsonl``; finished runs are skipped, so an
interrupted session resumes.

    python lm_gate5.py --data /kaggle/input/sd-lm --lang sd --out /kaggle/working
    python lm_gate5.py --data data/tasks/lm/sd --lang sd --out runs/lm_smoke --max-steps 30 --only unigram_V2000_s0
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

LN2 = math.log(2.0)


class Block(nn.Module):
    """Pre-norm transformer block with causal self-attention."""

    def __init__(self, d: int, heads: int, ff: int, dropout: float) -> None:
        super().__init__()
        self.ln1, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.attn = nn.MultiheadAttention(d, heads, dropout=dropout, batch_first=True)
        self.ff = nn.Sequential(nn.Linear(d, ff), nn.GELU(), nn.Linear(ff, d), nn.Dropout(dropout))

    def forward(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """Attention then feed-forward, both residual."""
        h = self.ln1(x)
        x = x + self.attn(h, h, h, attn_mask=mask, need_weights=False)[0]
        return x + self.ff(self.ln2(x))


class LM(nn.Module):
    """Small GPT-style LM with tied input/output embeddings."""

    def __init__(self, vocab: int, d: int, layers: int, heads: int, ctx: int, dropout: float) -> None:
        super().__init__()
        self.tok = nn.Embedding(vocab, d)
        self.pos = nn.Embedding(ctx, d)
        self.drop = nn.Dropout(dropout)
        self.blocks = nn.ModuleList(Block(d, heads, 4 * d, dropout) for _ in range(layers))
        self.ln = nn.LayerNorm(d)
        self.register_buffer("mask", torch.triu(torch.ones(ctx, ctx, dtype=torch.bool), 1), persistent=False)
        self.apply(self._init)

    @staticmethod
    def _init(m: nn.Module) -> None:
        """GPT-style init: N(0, 0.02) weights (N(0, 1) embeddings make tied logits explode)."""
        if isinstance(m, (nn.Linear, nn.Embedding)):
            nn.init.normal_(m.weight, 0.0, 0.02)
        if isinstance(m, nn.Linear) and m.bias is not None:
            nn.init.zeros_(m.bias)

    def forward(self, idx: torch.Tensor) -> torch.Tensor:
        """Next-token logits for every position."""
        t = idx.shape[1]
        x = self.drop(self.tok(idx) + self.pos(torch.arange(t, device=idx.device)))
        m = self.mask[:t, :t]
        for b in self.blocks:
            x = b(x, m)
        return self.ln(x) @ self.tok.weight.T


def token_nll(model: LM, stream: np.ndarray, ctx: int, device: str, bs: int = 64) -> np.ndarray:
    """Natural-log NLL of every token after the first (index i predicts stream[i+1])."""
    model.eval()
    n = len(stream)
    nll = np.zeros(n - 1, dtype=np.float64)
    half = ctx // 2
    starts = list(range(0, max(1, n - 1), half))
    windows = []
    for s in starts:
        e = min(s + ctx, n - 1)
        if e <= s:
            continue
        score_from = s if s == 0 else s + half  # first window scores everything
        if score_from >= e:
            continue
        windows.append((s, e, score_from))
    data = torch.from_numpy(stream.astype(np.int64))
    with torch.no_grad():
        for k in range(0, len(windows), bs):
            chunk = windows[k : k + bs]
            L = max(e - s for s, e, _ in chunk)
            x = torch.zeros(len(chunk), L, dtype=torch.long)
            y = torch.full((len(chunk), L), -100, dtype=torch.long)
            for j, (s, e, _) in enumerate(chunk):
                x[j, : e - s] = data[s:e]
                y[j, : e - s] = data[s + 1 : e + 1]
            x, y = x.to(device), y.to(device)
            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=device == "cuda"):
                logits = model(x)
            lp = (
                F.cross_entropy(logits.float().transpose(1, 2), y, reduction="none", ignore_index=-100)
                .cpu()
                .numpy()
            )
            for j, (s, e, f) in enumerate(chunk):
                nll[f:e] = lp[j, f - s : e - s]
    return nll


def bpc(nll: np.ndarray, stream: np.ndarray, n_chars: int) -> float:
    """Bits per character, excluding predictions of BOS (deterministic line starts)."""
    keep = stream[1:] != 1
    return float(nll[keep].sum() / LN2 / n_chars)


def run_one(path: Path, a: argparse.Namespace, device: str) -> dict:
    """Train and evaluate one tokenizer's LM."""
    z = np.load(path)
    seed = int(path.stem.rsplit("_s", 1)[1])
    torch.manual_seed(seed)
    np.random.seed(seed)
    vocab = int(z["vocab_size"])
    train, dev, test = z["train"], z["dev"], z["test"]
    model = LM(vocab, a.d_model, a.layers, a.heads, a.ctx, a.dropout).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=0.1, betas=(0.9, 0.95))
    scaler = torch.amp.GradScaler(device, enabled=device == "cuda")
    rng = np.random.default_rng(seed)
    tr = torch.from_numpy(train.astype(np.int64))
    best, best_state, bad, step, skipped = float("inf"), None, 0, 0, 0
    t0 = time.time()
    history = []
    while step < a.max_steps:
        model.train()
        lr = (
            a.lr
            * min(1.0, (step + 1) / a.warmup)
            * 0.5
            * (1 + math.cos(math.pi * min(1.0, step / a.max_steps)))
        )
        for g in opt.param_groups:
            g["lr"] = lr
        idx = rng.integers(0, len(train) - a.ctx - 1, size=a.batch)
        x = torch.stack([tr[i : i + a.ctx] for i in idx]).to(device)
        y = torch.stack([tr[i + 1 : i + a.ctx + 1] for i in idx]).to(device)
        with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=device == "cuda"):
            loss = F.cross_entropy(model(x).float().transpose(1, 2), y)
        opt.zero_grad(set_to_none=True)
        scaler.scale(loss).backward()
        scaler.unscale_(opt)
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        before = scaler.get_scale()
        scaler.step(opt)
        scaler.update()
        skipped += int(scaler.get_scale() < before)
        step += 1
        if step % a.eval_every == 0 or step == a.max_steps:
            d = bpc(token_nll(model, dev, a.ctx, device), dev, int(z["dev_n_chars"]))
            history.append((step, round(d, 5)))
            if d < best - 1e-4:
                best, bad = d, 0
                best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            elif step >= a.min_steps:
                bad += 1
                if bad >= a.patience:
                    break
    model.load_state_dict(best_state)
    nll = token_nll(model, test, a.ctx, device)
    word = z["test_word"][1:]
    keep = (test[1:] != 1) & (word >= 0)
    bits_per_word = np.bincount(word[keep], weights=nll[keep] / LN2, minlength=len(z["test_word_chars"]))
    chars = z["test_word_chars"].astype(np.float64)

    def strat(mask: np.ndarray) -> float | None:
        return float(bits_per_word[mask].sum() / chars[mask].sum()) if mask.any() else None

    held, oov = z["test_word_heldout"], z["test_word_oov"]
    name, v = path.stem.rsplit("_s", 1)[0].rsplit("_V", 1)
    return {
        "lang": a.lang, "tokenizer": name, "vocab": int(v), "seed": seed, "file": path.name,
        "dev_bpc": best, "test_bpc": bpc(nll, test, int(z["test_n_chars"])),
        "test_bpc_heldout_lemma": strat(held), "test_bpc_oov_form": strat(oov),
        "test_bpc_seen_form": strat(~oov), "n_heldout_words": int(held.sum()), "n_oov_words": int(oov.sum()),
        "tokens_per_char_test": float(len(test) / int(z["test_n_chars"])), "vocab_size": vocab,
        "params": sum(p.numel() for p in model.parameters()), "steps": step, "skipped_steps": skipped,
        "seconds": round(time.time() - t0, 1), "history": history, "device": device,
        "config": {k: getattr(a, k) for k in ("d_model", "layers", "heads", "ctx", "dropout", "lr", "batch",
                                               "max_steps", "min_steps", "eval_every", "patience", "warmup")},
    }  # fmt: skip


def main() -> int:
    """Run every (or the selected) tokenizer file; resume from the results file."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, required=True, help="directory with *.npz from 14_export_lm_data.py")
    ap.add_argument("--lang", required=True)
    ap.add_argument("--out", type=Path, default=Path("."))
    ap.add_argument("--only", nargs="*", default=None, help="file stems to run, e.g. unigram_V2000_s0")
    ap.add_argument("--d-model", dest="d_model", type=int, default=256)
    ap.add_argument("--layers", type=int, default=4)
    ap.add_argument("--heads", type=int, default=4)
    ap.add_argument("--ctx", type=int, default=256)
    ap.add_argument("--dropout", type=float, default=0.1)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--max-steps", dest="max_steps", type=int, default=6000)
    ap.add_argument("--min-steps", dest="min_steps", type=int, default=1500)
    ap.add_argument("--eval-every", dest="eval_every", type=int, default=250)
    ap.add_argument("--patience", type=int, default=4)
    ap.add_argument("--warmup", type=int, default=200)
    a = ap.parse_args()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    a.out.mkdir(parents=True, exist_ok=True)
    res = a.out / f"results_lm_{a.lang}.jsonl"
    done = set()
    if res.exists():
        done = {json.loads(ln)["file"] for ln in res.read_text(encoding="utf-8").splitlines() if ln.strip()}
    files = sorted(a.data.glob("*.npz"))
    if a.only:
        files = [f for f in files if f.stem in set(a.only)]
    print(f"device={device}; {len(files)} files; {len(done)} already done", flush=True)
    for f in files:
        if f.name in done:
            continue
        r = run_one(f, a, device)
        with res.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        print(f"{f.stem}: test bpc {r['test_bpc']:.4f} (held-out lemma {r['test_bpc_heldout_lemma']}) "
              f"steps {r['steps']} {r['seconds']}s", flush=True)  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
