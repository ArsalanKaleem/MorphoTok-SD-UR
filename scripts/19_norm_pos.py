"""Normalization x POS tagging (PREREG.md section 12): does sindhinorm help a tagger?

    python scripts/19_norm_pos.py --datasets sipos ud_sd            # the preregistered grid
    python scripts/19_norm_pos.py --smoke                            # pipeline check on dev only

For each (dataset, normalizer, system, seed) the same normalizer is applied to every token of
the training, dev and test text, a BiLSTM tagger (``morphtok.models.tagger``) is trained on the
training split with early stopping on dev, and it is scored on three test files built by
``scripts/18_build_norm_pos.py``: clean, keyboard-typed (``test_keyboard``) and the random-letter
control (``test_kbnoise``).

Normalizers: ``none``; ``freq`` = sindhinorm frequency mode (the 0.1.0 rules); ``keyboard`` =
sindhinorm keyboard mode (0.2.0 default). Both use the bundled word list.
Systems: ``word`` (whole-word embeddings, the representation most exposed to spelling) and
``char`` (character CNN). Each run writes a provenance record to ``runs/`` and one summary
line to ``results/norm_pos/runs_<dataset>.jsonl``.
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
sys.path.insert(0, str(ROOT / "packages" / "sindhinorm" / "src"))

TESTS = ("test", "test_keyboard", "test_kbnoise")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file."""
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def make_normalizer(name: str):  # type: ignore[no-untyped-def]
    """Token -> normalized token (cached); identity for ``none``."""
    if name == "none":
        return lambda t: t
    import sindhinorm

    norm = sindhinorm.Normalizer(
        sindhinorm.default_normalizer().lexicon, mode={"freq": "frequency", "keyboard": "keyboard"}[name]
    )
    cache: dict[str, str] = {}

    def apply(tok: str) -> str:
        if tok not in cache:
            cache[tok] = norm.normalize(tok)
        return cache[tok]

    return apply


def run_one(job: dict[str, Any]) -> dict[str, Any]:
    """Train and evaluate one tagger; returns the summary row."""
    import torch

    from morphtok.experiments.results import finalise, new_record
    from morphtok.models.tagger import Tagger, Vocab, make_batch, n_parameters

    torch.set_num_threads(job["threads"])
    ds, normalizer, system, seed = job["dataset"], job["normalizer"], job["system"], job["seed"]
    task = ROOT / "data" / "tasks" / ds
    apply = make_normalizer(normalizer)

    def prep(sents: list[dict]) -> list[dict]:
        return [{**s, "tokens": [apply(t) for t in s["tokens"]]} for s in sents]

    raw = {k: load_jsonl(task / f"{k}.jsonl") for k in ("train", "dev", *TESTS)}
    if job["smoke"]:
        raw["train"] = raw["train"][:300]
        kb = {"ي": "ی", "ه": "ہ", "ڪ": "ک"}  # smoke runs never touch the test split:
        raw["test"] = raw["dev"]  # dev stands in for test, retyped as in 18_build_norm_pos.py
        raw["test_keyboard"] = [
            {**s, "tokens": ["".join(kb.get(c, c) for c in t) for t in s["tokens"]],
             "perturbed": ["".join(kb.get(c, c) for c in t) != t for t in s["tokens"]]}
            for s in raw["dev"]
        ]  # fmt: skip
        raw["test_kbnoise"] = raw["dev"]
    data = {k: prep(v) for k, v in raw.items()}
    train, dev = data["train"], data["dev"]

    random.seed(seed)
    torch.manual_seed(seed)
    words = Vocab([t for s in train for t in s["tokens"]])
    chars = Vocab([c for s in train for t in s["tokens"] for c in t])
    pieces = Vocab([])
    tags = Vocab([u for s in train for u in s["upos"]])
    model = Tagger(system, len(tags), len(words), len(chars), len(pieces))
    opt = torch.optim.Adam(model.parameters(), lr=2e-3)
    loss_fn = torch.nn.CrossEntropyLoss(ignore_index=-100)

    def batches(sents: list[dict]) -> list:
        order = list(range(len(sents)))
        random.shuffle(order)
        return [make_batch([sents[i] for i in order[k : k + 32]], words, chars, pieces, tags, None)
                for k in range(0, len(order), 32)]  # fmt: skip

    def predict(sents: list[dict]) -> list[list[int]]:
        model.eval()
        out = []
        with torch.no_grad():
            for k in range(0, len(sents), 64):
                chunk = sents[k : k + 64]
                pred = model(make_batch(chunk, words, chars, pieces, tags, None)).argmax(-1)
                out += [pred[i, : len(s["tokens"])].tolist() for i, s in enumerate(chunk)]
        return out

    def bits(sents: list[dict]) -> str:
        return "".join("1" if p == tags(g) else "0" for s, ps in zip(sents, predict(sents), strict=True)
                       for p, g in zip(ps, s["upos"], strict=True))  # fmt: skip

    best, best_state, bad, epochs = -1.0, None, 0, 0
    t0 = time.time()
    for ep in range(job["epochs"]):
        model.train()
        for b in batches(train):
            opt.zero_grad()
            logits = model(b)
            loss_fn(logits.view(-1, logits.shape[-1]), b.tags.view(-1)).backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            opt.step()
        d = bits(dev)
        acc = d.count("1") / len(d)
        epochs = ep + 1
        if acc > best + 1e-6:
            best, bad, best_state = acc, 0, {k: v.clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= job["patience"]:
                break
    assert best_state is not None
    model.load_state_dict(best_state)

    b = {k: bits(data[k]) for k in TESTS}
    pert = "".join(
        "1" if m else "0"
        for s in raw["test_keyboard"]
        for m in s.get("perturbed", [False] * len(s["tokens"]))
    )
    restored = "".join(
        "1" if kb == cl else "0"
        for s_kb, s_cl in zip(data["test_keyboard"], data["test"], strict=True)
        for kb, cl in zip(s_kb["tokens"], s_cl["tokens"], strict=True)
    )

    def acc_on(x: str, mask: str | None = None) -> float:
        sel = [c for c, m in zip(x, mask or "1" * len(x), strict=True) if m == "1"]
        return sum(c == "1" for c in sel) / len(sel)

    m = {
        "acc_clean": acc_on(b["test"]), "acc_keyboard": acc_on(b["test_keyboard"]),
        "acc_kbnoise": acc_on(b["test_kbnoise"]),
        "acc_clean_pert": acc_on(b["test"], pert), "acc_keyboard_pert": acc_on(b["test_keyboard"], pert),
        "acc_kbnoise_pert": acc_on(b["test_kbnoise"], pert),
        "restored_pert": acc_on(restored, pert), "n_tokens": len(b["test"]), "n_pert": pert.count("1"),
        "dev_acc": best, "epochs": epochs, "params": n_parameters(model), "seconds": round(time.time() - t0, 1),
    }  # fmt: skip
    row = {
        "dataset": ds,
        "normalizer": normalizer,
        "system": system,
        "seed": seed,
        "smoke": job["smoke"],
        **m,
    }
    if not job["smoke"]:
        eid = f"SD-NORMPOS-{ds}-{normalizer}-{system}"
        rec = new_record(eid, seed, {"job": {k: v for k, v in job.items() if k != "threads"}},
                         {"name": ds, "language": "sd", "synthetic": False, "source": str(task)},
                         False, None, {}, {"name": f"{system}+{normalizer}"})  # fmt: skip
        rec["metrics"] = m
        rec["per_token"] = {**b, "perturbed_mask": pert, "restored": restored}
        finalise(rec, ROOT / "runs")
        out = ROOT / "results" / "norm_pos"
        out.mkdir(parents=True, exist_ok=True)
        with (out / f"runs_{ds}.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    return row


def main() -> int:
    """Run the grid in parallel processes."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datasets", nargs="*", default=["sipos", "ud_sd"])
    ap.add_argument("--normalizers", nargs="*", default=["none", "freq", "keyboard"])
    ap.add_argument("--systems", nargs="*", default=["word", "char"])
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--patience", type=int, default=4)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--threads", type=int, default=3)
    ap.add_argument("--smoke", action="store_true", help="300 training sentences, 2 epochs, dev only")
    a = ap.parse_args()
    if a.smoke:
        a.epochs, a.seeds, a.datasets = 2, 1, a.datasets[:1]
    jobs = [{"dataset": d, "normalizer": n, "system": s, "seed": k, "epochs": a.epochs,
             "patience": a.patience, "threads": a.threads, "smoke": a.smoke}
            for d in a.datasets for n in a.normalizers for s in a.systems for k in range(a.seeds)]  # fmt: skip
    print(f"{len(jobs)} runs; {a.jobs} parallel x {a.threads} threads", flush=True)
    with mp.get_context("spawn").Pool(a.jobs) as pool:
        for row in pool.imap_unordered(run_one, jobs):
            print(
                json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items()}),
                flush=True,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
