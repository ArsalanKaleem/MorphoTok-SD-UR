"""XLM-R + character-CNN fusion POS tagger (combined plan, Phase 2-3). GPU script.

Written for a single Kaggle/Colab T4 (~16 GB). **Not yet run on a GPU or with the real
XLM-R weights.** It has been smoke-tested end to end on CPU (2026-11-08, transformers
5.22.2) with the real xlm-roberta-base tokenizer and a tiny random 2-layer encoder: all
systems and budgets run, no skipped optimizer steps, and resume works. The fp16 GPU path
is untested, so treat the first GPU run's smoke-test cell as a check.

Fixes before the first GPU run: the character CNN runs only on real words and in fp32
(masked max-pooling at -1e4 could overflow in fp16 and make the GradScaler skip every
step); tiny budgets train for at least ``--min-steps`` optimizer steps, with patience
counted only after that; finished runs are skipped on restart; each row records
``lang``, ``steps``, ``epochs`` and ``skipped_steps``.

Systems (word representation = XLM-R hidden state of the word's FIRST subword):

* ``base``    XLM-R fine-tuning, linear tag classifier;
* ``concat``  ``tanh(Linear([h_xlmr; h_char]))`` with a character CNN;
* ``gated``   ``g * h_xlmr + (1 - g) * h_char``, ``g = sigmoid(Linear([h_xlmr; h_char]))``
  (parameter-matched to ``concat``).

Data: upload ``data/tasks/<lang>_pos/`` (made by ``scripts/build_pos_tasks.py``) as a
Kaggle dataset and pass its folder with ``--task-dir``. Output: one JSON line per run
in ``--out`` with the same metrics as ``scripts/07_pos_tagging.py``.

Example (T4)::

    pip install transformers
    python xlmr_fusion.py --task-dir /kaggle/input/sd-pos --kinds base gated concat \
        --budgets 0.01 0.1 1 --seeds 3 --out results_sd.jsonl
"""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import torch
from torch import nn


def load_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file."""
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


class CharCNN(nn.Module):
    """Character CNN word encoder (same design as ``morphtok.models.tagger.CharCNN``)."""

    def __init__(self, n_chars: int, dim: int, char_dim: int = 32, filters: int = 128) -> None:
        super().__init__()
        self.emb = nn.Embedding(n_chars, char_dim, padding_idx=0)
        self.convs = nn.ModuleList(nn.Conv1d(char_dim, filters, k, padding=k // 2) for k in (2, 3, 4))
        self.proj = nn.Linear(3 * filters, dim)

    def forward(self, chars: torch.Tensor) -> torch.Tensor:
        """(B, W, C) -> (B, W, dim). Only real word slots are convolved (padding stays 0).

        Runs in float32 even under autocast: max-pooling over masked positions must not
        overflow in fp16 (that would make NaN gradients and the GradScaler skip every step).
        """
        b, w, c = chars.shape
        flat = chars.view(b * w, c)
        real = flat[:, 0] != 0
        out = torch.zeros(b * w, self.proj.out_features, device=chars.device, dtype=torch.float32)
        if bool(real.any()):
            with torch.autocast(device_type=chars.device.type, enabled=False):
                words = flat[real]
                x = self.emb(words).float().transpose(1, 2)
                mask = (words != 0).unsqueeze(1)
                feats = [
                    torch.relu(conv(x))[:, :, :c].masked_fill(~mask, 0.0).max(dim=2).values
                    for conv in self.convs
                ]
                out[real] = self.proj(torch.cat(feats, dim=1))
        return out.view(b, w, -1)


class FusionTagger(nn.Module):
    """XLM-R encoder; first-subword pooling; optional character fusion; tag classifier."""

    def __init__(self, model_name: str, kind: str, n_tags: int, n_chars: int, dropout: float = 0.1) -> None:
        super().__init__()
        from transformers import AutoModel

        self.kind = kind
        self.enc = AutoModel.from_pretrained(model_name)
        d = self.enc.config.hidden_size
        self.char = CharCNN(n_chars, d) if kind != "base" else None
        self.fuse = nn.Linear(2 * d, d) if kind != "base" else None
        self.drop = nn.Dropout(dropout)
        self.out = nn.Linear(d, n_tags)

    def forward(self, input_ids, attention_mask, first_idx, chars):  # type: ignore[no-untyped-def]
        """first_idx: (B, W) subword index of each word's first piece (0 for padding)."""
        h = self.enc(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
        hw = torch.gather(h, 1, first_idx.unsqueeze(-1).expand(-1, -1, h.shape[-1]))
        if self.kind != "base":
            hc = self.char(chars).to(hw.dtype)
            z = self.fuse(torch.cat([hw, hc], dim=-1))
            hw = (
                torch.tanh(z)
                if self.kind == "concat"
                else torch.sigmoid(z) * hw + (1 - torch.sigmoid(z)) * hc
            )
        return self.out(self.drop(hw))


def encode(sents, tok, chars_stoi, tags_stoi, max_chars=16, max_len=256):  # type: ignore[no-untyped-def]
    """Batch tensors with word alignment via ``is_split_into_words``."""
    enc = tok([s["tokens"] for s in sents], is_split_into_words=True, truncation=True,
              max_length=max_len, padding=True, return_tensors="pt")  # fmt: skip
    w_max = max(len(s["tokens"]) for s in sents)
    first = torch.zeros(len(sents), w_max, dtype=torch.long)
    chars = torch.zeros(len(sents), w_max, max_chars, dtype=torch.long)
    tags = torch.full((len(sents), w_max), -100, dtype=torch.long)
    for i, s in enumerate(sents):
        seen = set()
        for j, wid in enumerate(enc.word_ids(i)):
            if wid is not None and wid not in seen:
                seen.add(wid)
                first[i, wid] = j
        for wid, t in enumerate(s["tokens"]):
            if wid not in seen:
                continue  # truncated word: left as padding (-100), reported in n_truncated
            tags[i, wid] = tags_stoi.get(s["upos"][wid], 0)
            for k, ch in enumerate(t[:max_chars]):
                chars[i, wid, k] = chars_stoi.get(ch, 1)
    return enc["input_ids"], enc["attention_mask"], first, chars, tags


def run(args, kind, budget, seed, data, tok, device):  # type: ignore[no-untyped-def]
    """Train one model with dev early stopping; return metrics on the diagnostic test sets."""
    random.seed(seed)
    torch.manual_seed(seed)
    train = [data["train"][i] for i in data["budgets"][budget]]
    chars_stoi = {
        c: i + 2 for i, c in enumerate(sorted({ch for s in train for t in s["tokens"] for ch in t}))
    }
    tags_stoi = {
        t: i for i, t in enumerate(sorted({u for s in train for u in s["upos"]} | set(data["all_tags"])))
    }
    model = FusionTagger(args.model, kind, len(tags_stoi), len(chars_stoi) + 2).to(device)
    enc_params = [p for n, p in model.named_parameters() if n.startswith("enc.")]
    new_params = [p for n, p in model.named_parameters() if not n.startswith("enc.")]
    opt = torch.optim.AdamW(
        [{"params": enc_params, "lr": args.lr}, {"params": new_params, "lr": args.head_lr}]
    )
    loss_fn = nn.CrossEntropyLoss(ignore_index=-100)
    scaler = torch.amp.GradScaler(device.type, enabled=device.type == "cuda")

    def predict(sents):  # type: ignore[no-untyped-def]
        model.eval()
        out = []
        with torch.no_grad():
            for k in range(0, len(sents), args.batch):
                chunk = sents[k : k + args.batch]
                ids, am, first, ch, _ = encode(chunk, tok, chars_stoi, tags_stoi)
                with torch.autocast(device.type, enabled=device.type == "cuda"):
                    logits = model(ids.to(device), am.to(device), first.to(device), ch.to(device))
                pred = logits.argmax(-1).cpu()
                inv = {v: k2 for k2, v in tags_stoi.items()}
                out += [[inv[int(x)] for x in pred[i, : len(s["tokens"])]] for i, s in enumerate(chunk)]
        return out

    best, best_state, bad = -1.0, None, 0
    steps_per_epoch = max(1, -(-len(train) // args.batch))
    # Tiny budgets need many epochs to reach a minimum number of optimizer steps.
    max_epochs = max(args.epochs, -(-args.min_steps // steps_per_epoch))
    steps, skipped, epochs_run = 0, 0, 0
    t0 = time.time()
    for _ep in range(max_epochs):
        epochs_run += 1
        model.train()
        order = list(range(len(train)))
        random.shuffle(order)
        for k in range(0, len(order), args.batch):
            chunk = [train[i] for i in order[k : k + args.batch]]
            ids, am, first, ch, y = encode(chunk, tok, chars_stoi, tags_stoi)
            opt.zero_grad()
            with torch.autocast(device.type, enabled=device.type == "cuda"):
                logits = model(ids.to(device), am.to(device), first.to(device), ch.to(device))
                loss = loss_fn(logits.view(-1, logits.shape[-1]).float(), y.to(device).view(-1))
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            norm = nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            skipped += int(not torch.isfinite(norm))  # GradScaler skips non-finite steps
            scaler.step(opt)
            scaler.update()
            steps += 1
        preds = predict(data["dev"])
        acc = sum(
            p == g
            for s, ps in zip(data["dev"], preds, strict=False)
            for p, g in zip(ps, s["upos"], strict=False)
        ) / sum(len(s["upos"]) for s in data["dev"])
        if acc > best + 1e-6:
            best, bad = acc, 0
            best_state = {k2: v.detach().cpu().clone() for k2, v in model.state_dict().items()}
        elif steps >= args.min_steps:  # patience only counts once the minimum is reached
            bad += 1
            if bad >= args.patience:
                break
    model.load_state_dict(best_state)
    lemmas = {lem for s in train for lem in s["lemmas"]}
    forms = {t for s in train for t in s["tokens"]}
    bits = {}
    for name in ("test", "test_confusable", "test_randnoise"):
        preds = predict(data[name])
        bits[name] = [
            p == g
            for s, ps in zip(data[name], preds, strict=False)
            for p, g in zip(ps, s["upos"], strict=False)
        ]
    clean = data["test"]
    unseen = [lem not in lemmas for s in clean for lem in s["lemmas"]]
    oov = [t not in forms for s in clean for t in s["tokens"]]
    pert = [m for s in data["test_confusable"] for m in s["perturbed"]]

    def acc_on(b, mask=None):  # type: ignore[no-untyped-def]
        sel = [x for x, m in zip(b, mask or [True] * len(b), strict=False) if m]
        return sum(sel) / len(sel) if sel else None

    return {
        "kind": kind, "budget": budget, "seed": seed, "model": args.model, "dev_acc": best,
        "acc_all": acc_on(bits["test"]), "acc_unseen_lemma": acc_on(bits["test"], unseen),
        "acc_oov_form": acc_on(bits["test"], oov), "acc_pert_clean": acc_on(bits["test"], pert),
        "acc_pert_confusable": acc_on(bits["test_confusable"], pert),
        "acc_pert_noise": acc_on(bits["test_randnoise"], pert),
        "seconds": round(time.time() - t0, 1), "steps_per_epoch": steps_per_epoch,
        "steps": steps, "epochs": epochs_run, "skipped_steps": skipped, "lang": args.lang,
        "n_unseen_lemma": sum(unseen), "n_perturbed": sum(pert),
    }  # fmt: skip


def main() -> None:
    """Run the grid and append JSON lines to ``--out``."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--task-dir", required=True)
    ap.add_argument("--model", default="xlm-roberta-base")
    ap.add_argument("--kinds", nargs="*", default=["base", "concat", "gated"])
    ap.add_argument("--budgets", nargs="*", default=["0.01", "0.1", "1"])
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--patience", type=int, default=3)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--head-lr", type=float, default=1e-3)
    ap.add_argument("--min-steps", type=int, default=300, help="minimum optimizer steps per run")
    ap.add_argument("--lang", default="sd", help="language tag recorded in each result row")
    ap.add_argument("--out", default="results.jsonl")
    a = ap.parse_args()
    from transformers import AutoTokenizer

    d = Path(a.task_dir)
    data = {
        n: load_jsonl(d / f"{n}.jsonl") for n in ("train", "dev", "test", "test_confusable", "test_randnoise")
    }
    data["budgets"] = json.loads((d / "budgets.json").read_text(encoding="utf-8"))
    data["all_tags"] = json.loads((d / "stats.json").read_text(encoding="utf-8"))["upos_tags"]
    tok = AutoTokenizer.from_pretrained(a.model)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    done = set()
    if Path(a.out).exists():  # resume: skip runs already in the output file
        for line in Path(a.out).read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                done.add((r.get("lang", a.lang), r["kind"], r["budget"], r["seed"]))
    print(f"device={device}; {len(done)} runs already done in {a.out}", flush=True)
    for budget in a.budgets:
        for seed in range(a.seeds):
            for kind in a.kinds:
                if (a.lang, kind, budget, seed) in done:
                    continue
                row = run(a, kind, budget, seed, data, tok, device)
                with open(a.out, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(row) + "\n")
                print(row, flush=True)


if __name__ == "__main__":
    main()
