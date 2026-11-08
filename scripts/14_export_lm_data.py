"""Export token-id streams for the Gate 5 language-model study (H7), one file per tokenizer.

Encodes the pilot corpus splits with every trained pilot tokenizer (the same models as the
preregistered test, ``runs/<LANG>-models/manifest.json``), so the GPU script needs only
numpy and torch. Each line becomes ``BOS w1 SEP w2 SEP ... wn EOS``; the separator after a
word counts as part of that word.

Bits per character (bpc) is comparable across tokenizers because every tokenizer encodes
the same NFC text losslessly and the character count is fixed in advance:
``n_chars = sum(len(word) + 1)`` over words (the +1 is the following space or line end).

Per test word we store its character count, whether its lemma is held out from tokenizer
supervision (silver entry in the dev/test lemma split), and whether its form occurs in the
LM training lines, for stratified bpc.

    python scripts/14_export_lm_data.py --config configs/run/pilot_wiki.yaml --data sindhi
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from morphtok.data.loaders import load_gold
from morphtok.data.normalize import split_words, strip_format
from morphtok.experiments.runner import REPO_ROOT, build_analyzer, cli, exp_id, load_dataset, make_pipeline
from morphtok.tokenizers.baselines import tokenizer_from_dict

TOKENIZERS = ("unigram", "unigram_hard_trainonly", "bpe")
PAD, BOS, EOS, SEP = 0, 1, 2, 3


def _args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--dest", default="data/tasks/lm")


def main() -> int:
    """Write ``<dest>/<lang>/<tokenizer>_V<v>_s<seed>.npz`` and ``meta.json``."""
    args, run, out = cli(__doc__ or "", _args)
    ds = load_dataset(run)
    lang = ds.cfg.language
    dest = REPO_ROOT / args.dest / lang
    dest.mkdir(parents=True, exist_ok=True)
    gold = load_gold(ds.cfg)
    heldout = {w for w, g in gold.items() if g.split in ("dev", "test")}
    splits = {k: ds.splits[k] for k in ("train", "dev", "test")}
    train_forms = {strip_format(w)[0] for ln in splits["train"] for w in split_words(ln)}
    manifest = json.loads((out / exp_id("models", ds) / "manifest.json").read_text(encoding="utf-8"))
    analyzer = build_analyzer(ds)
    meta: dict = {"lang": lang, "lines": {k: len(v) for k, v in splits.items()}, "files": []}
    for m in manifest:
        name, vocab, seed = m["tokenizer"], int(m["vocab"]), int(m["seed"])
        if name not in TOKENIZERS:
            continue
        pipe = make_pipeline(run["tokenizer_cfgs"][name], vocab, analyzer)
        pipe.tokenizer = tokenizer_from_dict(json.loads((out / m["path"]).read_text(encoding="utf-8")))
        ids: dict[str, int] = {}
        cache: dict[str, list[int]] = {}

        def enc(word: str, pipe=pipe, cache=cache, ids=ids, name=name) -> tuple[list[int], int]:
            """Token ids and canonical length of one word (cached)."""
            if word not in cache:
                pw, toks = pipe.encode_word(word)
                if "".join(toks) != pw.canonical:
                    raise ValueError(f"lossy encoding of {word!r} by {name}")
                cache[word] = [ids.setdefault(t, len(ids) + 4) for t in toks]
                cache[word + "\0len"] = [len(pw.canonical)]
            return cache[word], cache[word + "\0len"][0]

        arrays: dict[str, np.ndarray] = {}
        for split, lines in splits.items():
            stream: list[int] = []
            word_of: list[int] = []
            w_chars: list[int] = []
            w_held: list[bool] = []
            w_oov: list[bool] = []
            n_chars = 0
            for ln in lines:
                words = split_words(ln)
                if not words:
                    continue
                stream.append(BOS)
                word_of.append(-1)
                for k, w in enumerate(words):
                    toks, nc = enc(w)
                    wid = len(w_chars)
                    stream += [*toks, EOS if k == len(words) - 1 else SEP]
                    word_of += [wid] * (len(toks) + 1)
                    stripped = strip_format(w)[0]
                    w_chars.append(nc + 1)
                    w_held.append(stripped in heldout)
                    w_oov.append(stripped not in train_forms)
                    n_chars += nc + 1
            arrays[split] = np.asarray(stream, dtype=np.int32)
            arrays[f"{split}_n_chars"] = np.asarray(n_chars, dtype=np.int64)
            if split == "test":
                arrays["test_word"] = np.asarray(word_of, dtype=np.int32)
                arrays["test_word_chars"] = np.asarray(w_chars, dtype=np.int32)
                arrays["test_word_heldout"] = np.asarray(w_held, dtype=bool)
                arrays["test_word_oov"] = np.asarray(w_oov, dtype=bool)
        arrays["vocab_size"] = np.asarray(len(ids) + 4, dtype=np.int64)
        fname = f"{name}_V{vocab}_s{seed}.npz"
        np.savez_compressed(dest / fname, **arrays)
        info = {"file": fname, "tokenizer": name, "vocab": vocab, "seed": seed, "model_run_id": m["run_id"],
                "vocab_size": len(ids) + 4, **{f"{s}_tokens": int(arrays[s].size) for s in splits},
                **{f"{s}_chars": int(arrays[f"{s}_n_chars"]) for s in splits}}  # fmt: skip
        meta["files"].append(info)
        print(info)
    (dest / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
