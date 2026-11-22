"""Build the task files for the normalization x POS-tagging study (PREREG.md section 12).

    python scripts/18_build_norm_pos.py

Two datasets, each written to ``data/tasks/<name>/`` (git-ignored, derived from licensed data):

* ``sipos``: SiPOS (Ali et al., 2021; Sindhi news, 293,683 tokens, UPOS tags). The file has no
  sentence boundaries, so sentences end at ``. ؟ ! ? ۔``. Sentences are assigned to
  train/dev/test (80/10/10) by a salted SHA-256 of their text. Tags are stripped of spaces;
  the single row tagged ``\"\"\"`` is dropped.
* ``ud_sd``: UD Sindhi-Isra, the official splits already in ``data/tasks/sd_pos/``.

For each dataset two extra test files hold the *same* sentences:

* ``test_keyboard.jsonl``: the text as an Urdu keyboard would type it. Every token containing a
  Sindhi letter that the keyboard lacks or types differently gets the substitution for every
  occurrence: ي -> ی (Farsi yeh), ه -> ہ (heh goal), ڪ -> ک (keheh). Other Sindhi-only letters
  (ٻ ڄ ڏ ...) are left as they are, so this models the look-alike substitutions only.
* ``test_kbnoise.jsonl``: control. The same tokens get one random letter replaced by a
  different letter of the training alphabet (seeded), so the number of altered tokens matches.

A per-token ``perturbed`` mask marks the altered tokens in both files.
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIPOS = ROOT / "data" / "raw" / "sipos" / "SiPOS" / "SiPOS tagset.txt"
UD = ROOT / "data" / "tasks" / "sd_pos"
OUT = ROOT / "data" / "tasks"
SALT = "sipos-split-v1"
ENDERS = {".", "؟", "!", "?", "۔"}
KEYBOARD = {"ي": "ی", "ه": "ہ", "ڪ": "ک"}


def load_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file."""
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    """Write a JSONL file."""
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def sipos_sentences() -> list[dict]:
    """SiPOS as sentences of (token, UPOS)."""
    rows = [ln.split("\t") for ln in SIPOS.read_text(encoding="utf-8").splitlines()[1:] if ln.strip()]
    sents, cur_t, cur_u = [], [], []
    for tok, _tag, upos, _spos in (r for r in rows if len(r) == 4):
        upos = upos.strip()
        if upos == '"""':
            continue
        cur_t.append(tok.strip())
        cur_u.append(upos)
        if tok.strip() in ENDERS:
            sents.append((cur_t, cur_u))
            cur_t, cur_u = [], []
    if cur_t:
        sents.append((cur_t, cur_u))
    return [{"id": f"sipos-{i:05d}", "tokens": t, "upos": u} for i, (t, u) in enumerate(sents)]


def split_of(sent: dict) -> str:
    """Assign train, dev or test by a salted hash of the sentence text."""
    h = int(hashlib.sha256((SALT + " ".join(sent["tokens"])).encode("utf-8")).hexdigest(), 16) % 10
    return "train" if h < 8 else ("dev" if h == 8 else "test")


def perturb(test: list[dict], alphabet: list[str], seed: int = 13) -> tuple[list[dict], list[dict]]:
    """Keyboard-typed copy and random-letter control of the test sentences."""
    rng = random.Random(seed)
    kb, noise = [], []
    for s in test:
        k_toks, n_toks, mask = [], [], []
        for t in s["tokens"]:
            typed = "".join(KEYBOARD.get(c, c) for c in t)
            changed = typed != t
            mask.append(changed)
            k_toks.append(typed)
            if changed:
                pos = rng.randrange(len(t))
                n_toks.append(t[:pos] + rng.choice([a for a in alphabet if a != t[pos]]) + t[pos + 1 :])
            else:
                n_toks.append(t)
        kb.append({**s, "tokens": k_toks, "perturbed": mask})
        noise.append({**s, "tokens": n_toks, "perturbed": mask})
    return kb, noise


def build(name: str, splits: dict[str, list[dict]]) -> dict:
    """Write one dataset and return its statistics."""
    dest = OUT / name
    dest.mkdir(parents=True, exist_ok=True)
    for k, v in splits.items():
        write_jsonl(dest / f"{k}.jsonl", v)
    alphabet = sorted({c for s in splits["train"] for t in s["tokens"] for c in t if c.isalpha()})
    kb, noise = perturb(splits["test"], alphabet)
    write_jsonl(dest / "test_keyboard.jsonl", kb)
    write_jsonl(dest / "test_kbnoise.jsonl", noise)
    n_test = sum(len(s["tokens"]) for s in splits["test"])
    n_pert = sum(sum(s["perturbed"]) for s in kb)
    stats = {
        "sentences": {k: len(v) for k, v in splits.items()},
        "tokens": {k: sum(len(s["tokens"]) for s in v) for k, v in splits.items()},
        "test_tokens_perturbed": n_pert,
        "test_share_perturbed": round(n_pert / n_test, 4),
        "upos": dict(Counter(u for s in splits["train"] for u in s["upos"]).most_common()),
    }
    (dest / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    return stats


def main() -> int:
    """Build both datasets."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    sents = sipos_sentences()
    sp: dict[str, list[dict]] = {"train": [], "dev": [], "test": []}
    for s in sents:
        sp[split_of(s)].append(s)
    print("sipos", json.dumps(build("sipos", sp), ensure_ascii=False)[:400])
    ud = {k: [{"id": s["id"], "tokens": s["tokens"], "upos": s["upos"]} for s in load_jsonl(UD / f"{k}.jsonl")]
          for k in ("train", "dev", "test")}  # fmt: skip
    print("ud_sd", json.dumps(build("ud_sd", ud), ensure_ascii=False)[:400])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
