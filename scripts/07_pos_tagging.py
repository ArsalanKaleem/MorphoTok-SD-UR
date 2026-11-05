"""POS-tagging study (combined plan): where should morphological information enter?

Trains BiLSTM taggers that differ only in word representation (``morphtok.models.tagger``)
on nested low-resource budgets of the official UD training split, over several seeds,
and evaluates on:

* the clean UD test set, split into **unseen-lemma** tokens (lemma absent from the training
  budget), seen-lemma tokens and unseen-form tokens;
* ``test_confusable``: visually confusable code-point substitution on ~40-47% of tokens
  (hypothesis pending native review), scored on the perturbed tokens only;
* ``test_randnoise``: the same tokens with one random letter changed (control).

Systems: ``word``, ``char``, ``sub:<tok>``, ``concat:<tok>``, ``gated:<tok>``, where ``<tok>``
names a tokenizer trained by ``03_train_tokenizers.py --config configs/run/pilot_postok.yaml``
on Wikipedia (``unigram_hard_trainonly`` is supervised only by UD *train* lemmas).

Every run is a provenance record in ``runs/`` with per-token correctness for paired analysis
(``scripts/08_pos_report.py``). Prereq: ``scripts/build_pos_tasks.py``.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import random
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

LANG_NAME = {"sd": "sindhi", "ur": "urdu"}
DEFAULT_SYSTEMS = [
    "word",
    "char",
    "sub:bpe",
    "sub:unigram",
    "sub:unigram_hard_trainonly",
    "concat:unigram",
    "gated:unigram",
    "gated:unigram_hard_trainonly",
]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file."""
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def load_segmenter(lang: str, tok_name: str):  # type: ignore[no-untyped-def]
    """Word -> pieces function for a tokenizer trained for the POS study (cached)."""
    from morphtok.config import load_yaml
    from morphtok.experiments.runner import make_pipeline
    from morphtok.tokenizers.baselines import tokenizer_from_dict

    mdir = ROOT / "runs" / f"{lang.upper()}-{LANG_NAME[lang]}_postok-models"
    manifest = json.loads((mdir / "manifest.json").read_text(encoding="utf-8"))
    entry = next(m for m in manifest if m["tokenizer"] == tok_name)
    cfg = load_yaml(f"configs/tokenizer/{tok_name}.yaml")
    pipe = make_pipeline(cfg, int(entry["vocab"]), analyzer=None)  # inference needs no analyzer
    pipe.tokenizer = tokenizer_from_dict(
        json.loads((ROOT / "runs" / entry["path"]).read_text(encoding="utf-8"))
    )
    cache: dict[str, list[str]] = {}

    def segment(word: str) -> list[str]:
        if word not in cache:
            cache[word] = pipe.encode_word(word)[1] or [word]
        return cache[word]

    return segment, entry["run_id"]


def run_one(job: dict[str, Any]) -> dict[str, Any]:
    """Train and evaluate one (system, budget, seed); returns a summary row."""
    import torch

    from morphtok.experiments.results import finalise, new_record
    from morphtok.models.tagger import Tagger, Vocab, make_batch, n_parameters

    torch.set_num_threads(job["threads"])
    lang, system, budget, seed = job["lang"], job["system"], job["budget"], job["seed"]
    task = ROOT / "data" / "tasks" / f"{lang}_pos"
    train_all = load_jsonl(task / "train.jsonl")
    idx = json.loads((task / "budgets.json").read_text(encoding="utf-8"))[budget]
    train = [train_all[i] for i in idx]
    dev = load_jsonl(task / "dev.jsonl")
    tests = {
        name: load_jsonl(task / f"{name}.jsonl") for name in ("test", "test_confusable", "test_randnoise")
    }
    kind, _, tok = system.partition(":")
    segment, tok_run = load_segmenter(lang, tok) if tok else (None, None)

    random.seed(seed)
    torch.manual_seed(seed)
    words = Vocab([t for s in train for t in s["tokens"]])
    chars = Vocab([ch for s in train for t in s["tokens"] for ch in t])
    pieces = Vocab([p for s in train for t in s["tokens"] for p in segment(t)] if segment else [])
    tags = Vocab([u for s in train for u in s["upos"]])
    model = Tagger(kind, len(tags), len(words), len(chars), len(pieces))
    opt = torch.optim.Adam(model.parameters(), lr=2e-3)
    loss_fn = torch.nn.CrossEntropyLoss(ignore_index=-100)

    def batches(sents: list[dict], shuffle: bool) -> list:
        order = list(range(len(sents)))
        if shuffle:
            random.shuffle(order)
        return [make_batch([sents[i] for i in order[k : k + 32]], words, chars, pieces, tags, segment)
                for k in range(0, len(order), 32)]  # fmt: skip

    def predict(sents: list[dict]) -> list[list[int]]:
        model.eval()
        out = []
        with torch.no_grad():
            for k in range(0, len(sents), 64):
                chunk = sents[k : k + 64]
                b = make_batch(chunk, words, chars, pieces, tags, segment)
                pred = model(b).argmax(-1)
                for i, s in enumerate(chunk):
                    out.append(pred[i, : len(s["tokens"])].tolist())
        return out

    best_acc, best_state, bad, epochs = -1.0, None, 0, 0
    t0 = time.time()
    for ep in range(job["epochs"]):
        model.train()
        for b in batches(train, shuffle=True):
            opt.zero_grad()
            logits = model(b)
            loss = loss_fn(logits.view(-1, logits.shape[-1]), b.tags.view(-1))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            opt.step()
        preds = predict(dev)
        corr = sum(
            p == tags(g) for s, ps in zip(dev, preds, strict=True) for p, g in zip(ps, s["upos"], strict=True)
        )
        acc = corr / sum(len(s["tokens"]) for s in dev)
        epochs = ep + 1
        if acc > best_acc + 1e-6:
            best_acc, bad = acc, 0
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= job["patience"]:
                break
    assert best_state is not None
    model.load_state_dict(best_state)

    train_lemmas = {lem for s in train for lem in s["lemmas"]}
    train_forms = {t for s in train for t in s["tokens"]}
    clean = tests["test"]
    bits: dict[str, str] = {}
    for name, sents in tests.items():
        preds = predict(sents)
        bits[name] = "".join("1" if p == tags(g) else "0" for s, ps in zip(sents, preds, strict=True)
                             for p, g in zip(ps, s["upos"], strict=True))  # fmt: skip
    unseen = "".join("1" if lem not in train_lemmas else "0" for s in clean for lem in s["lemmas"])
    oov = "".join("1" if t not in train_forms else "0" for s in clean for t in s["tokens"])
    pert = "".join("1" if m else "0" for s in tests["test_confusable"] for m in s["perturbed"])

    def acc_on(b: str, mask: str | None = None) -> tuple[float | None, int]:
        sel = [x for x, m in zip(b, mask or "1" * len(b), strict=True) if m == "1"]
        return (sum(x == "1" for x in sel) / len(sel) if sel else None), len(sel)

    m: dict[str, Any] = {}
    for key, b, mask in [
        ("acc_all", bits["test"], None),
        ("acc_unseen_lemma", bits["test"], unseen),
        ("acc_seen_lemma", bits["test"], "".join("1" if u == "0" else "0" for u in unseen)),
        ("acc_oov_form", bits["test"], oov),
        ("acc_pert_clean", bits["test"], pert),
        ("acc_pert_confusable", bits["test_confusable"], pert),
        ("acc_pert_noise", bits["test_randnoise"], pert),
    ]:
        m[key], m["n_" + key[4:]] = acc_on(b, mask)
    m.update({"dev_acc": best_acc, "epochs": epochs, "params": n_parameters(model),
              "train_sentences": len(train), "seconds": round(time.time() - t0, 1),
              "gate_mean_last_batch": model.last_gate_mean})  # fmt: skip
    eid = f"{lang.upper()}-POS-{system.replace(':', '_')}-B{budget}"
    rec = new_record(eid, seed, {"job": {k: v for k, v in job.items() if k != "threads"}},
                     {"name": f"ud_{lang}", "language": lang, "synthetic": False,
                      "source": "UD official splits", "tokenizer_run_id": tok_run},
                     False, len(pieces) if segment else None, {}, {"name": system})  # fmt: skip
    rec["metrics"] = m
    rec["per_token"] = {**bits, "unseen_lemma_mask": unseen, "oov_mask": oov, "perturbed_mask": pert}
    finalise(rec, ROOT / "runs")
    return {
        "system": system,
        "budget": budget,
        "seed": seed,
        **{
            k: m[k]
            for k in ("acc_all", "acc_unseen_lemma", "acc_pert_confusable", "acc_pert_noise", "seconds")
        },
    }


def main() -> int:
    """Run the grid in parallel processes."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lang", default="sd", choices=sorted(LANG_NAME))
    ap.add_argument("--systems", nargs="*", default=DEFAULT_SYSTEMS)
    ap.add_argument("--budgets", nargs="*", default=["0.01", "0.05", "0.1", "0.25", "1"])
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--low-budget-seeds", type=int, default=5, help="seeds for budgets <= 0.1")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--patience", type=int, default=4)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--threads", type=int, default=3)
    a = ap.parse_args()
    jobs = []
    for budget in a.budgets:
        n = a.low_budget_seeds if float(budget) <= 0.1 else a.seeds
        for seed in range(n):
            for system in a.systems:
                jobs.append({"lang": a.lang, "system": system, "budget": budget, "seed": seed,
                             "epochs": a.epochs, "patience": a.patience, "threads": a.threads})  # fmt: skip
    print(f"{len(jobs)} runs; {a.jobs} parallel jobs x {a.threads} threads")
    ctx = mp.get_context("spawn")
    with ctx.Pool(a.jobs) as pool:
        for row in pool.imap_unordered(run_one, jobs):
            print(json.dumps(row), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
