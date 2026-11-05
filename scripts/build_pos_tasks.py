"""Build POS-tagging task files with diagnostic test sets (combined plan, Phase 1).

Input: official UD splits in ``data/raw/ud/`` (Sindhi-Isra, Urdu-UDTB).
Output: ``data/tasks/<lang>_pos/`` (git-ignored; derived from licensed data)

* ``{train,dev,test}.jsonl``: one sentence per line ``{"id", "tokens", "upos", "lemmas"}``.
  Multiword-token ranges and empty nodes are skipped (word level, as in UD UPOS scoring).
* ``budgets.json``: nested training subsets (fractions of train sentences; one fixed
  shuffle, so each smaller budget is a subset of every larger one).
* ``test_confusable.jsonl``: the test set with a **visually confusable code-point
  substitution** applied to every token that contains the source code point, plus a
  per-token ``perturbed`` mask. Default substitutions (a *hypothesis*, pending the
  native-speaker letter-variant review, see ``audit/REVIEWING.md`` Task 3):
  Sindhi: Arabic yeh U+064A -> Farsi yeh U+06CC (Urdu-keyboard spelling seen in Sindhi
  Wikipedia); Urdu: Farsi yeh U+06CC -> Arabic yeh U+064A and keheh U+06A9 -> Arabic kaf
  U+0643 (off-standard forms seen in Urdu Wikipedia/web).
* ``test_randnoise.jsonl``: control. The **same tokens** each get one random letter
  replaced by a different letter of the training alphabet (seeded), so edit count and
  positions-per-token match the confusable set but the edit is arbitrary.

Unseen-lemma status is computed at evaluation time relative to the training budget used.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UD = ROOT / "data" / "raw" / "ud"
FILES = {"sd": "sd_isra-ud-{}.conllu", "ur": "ur_udtb-ud-{}.conllu"}
SUBST = {"sd": {"ي": "ی"}, "ur": {"ی": "ي", "ک": "ك"}}
BUDGETS = (0.01, 0.05, 0.10, 0.25, 0.50, 1.00)


def read_conllu(path: Path) -> list[dict[str, object]]:
    """Sentences with word-level tokens, UPOS and lemmas."""
    sents: list[dict[str, object]] = []
    cur: dict[str, object] = {"id": None, "tokens": [], "upos": [], "lemmas": []}
    for line in [*path.read_text(encoding="utf-8").splitlines(), ""]:
        if not line.strip():
            if cur["tokens"]:
                sents.append(cur)
            cur = {"id": None, "tokens": [], "upos": [], "lemmas": []}
            continue
        if line.startswith("# sent_id"):
            cur["id"] = line.split("=", 1)[1].strip()
            continue
        if line.startswith("#"):
            continue
        cols = line.split("\t")
        if "-" in cols[0] or "." in cols[0]:
            continue
        cur["tokens"].append(cols[1])  # type: ignore[union-attr]
        cur["upos"].append(cols[3])  # type: ignore[union-attr]
        cur["lemmas"].append(cols[2])  # type: ignore[union-attr]
    return sents


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    """One JSON object per line."""
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def perturb(
    test: list[dict], subst: dict[str, str], alphabet: list[str], seed: int
) -> tuple[list[dict], list[dict]]:
    """Confusable-substitution test set and a matched random-letter control."""
    rng = random.Random(seed)
    conf, noise = [], []
    for s in test:
        c_toks, n_toks, mask = [], [], []
        for t in s["tokens"]:
            if any(ch in subst for ch in t):
                c_toks.append("".join(subst.get(ch, ch) for ch in t))
                letters = [i for i, ch in enumerate(t) if ch.isalpha()]
                i = rng.choice(letters)
                repl = rng.choice([a for a in alphabet if a != t[i]])
                n_toks.append(t[:i] + repl + t[i + 1 :])
                mask.append(True)
            else:
                c_toks.append(t)
                n_toks.append(t)
                mask.append(False)
        conf.append({**s, "tokens": c_toks, "perturbed": mask})
        noise.append({**s, "tokens": n_toks, "perturbed": mask})
    return conf, noise


def main() -> int:
    """Write task files for the requested languages."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("langs", nargs="*", default=["sd", "ur"])
    ap.add_argument("--seed", type=int, default=13)
    a = ap.parse_args()
    for lang in a.langs:
        out = ROOT / "data" / "tasks" / f"{lang}_pos"
        out.mkdir(parents=True, exist_ok=True)
        splits = {sp: read_conllu(UD / FILES[lang].format(sp)) for sp in ("train", "dev", "test")}
        for sp, rows in splits.items():
            write_jsonl(out / f"{sp}.jsonl", rows)
        order = list(range(len(splits["train"])))
        random.Random(a.seed).shuffle(order)
        budgets = {f"{b:g}": sorted(order[: max(1, round(b * len(order)))]) for b in BUDGETS}
        (out / "budgets.json").write_text(json.dumps(budgets), encoding="utf-8")
        alphabet = sorted({ch for s in splits["train"] for t in s["tokens"] for ch in t if ch.isalpha()})
        conf, noise = perturb(splits["test"], SUBST[lang], alphabet, a.seed)
        write_jsonl(out / "test_confusable.jsonl", conf)
        write_jsonl(out / "test_randnoise.jsonl", noise)
        train_lemmas = {lem for s in splits["train"] for lem in s["lemmas"]}
        n_test = sum(len(s["tokens"]) for s in splits["test"])
        unseen = sum(1 for s in splits["test"] for lem in s["lemmas"] if lem not in train_lemmas)
        pert = sum(sum(s["perturbed"]) for s in conf)
        stats = {
            "lang": lang,
            "sentences": {k: len(v) for k, v in splits.items()},
            "tokens": {k: sum(len(s["tokens"]) for s in v) for k, v in splits.items()},
            "test_unseen_lemma_tokens_vs_full_train": unseen,
            "test_unseen_lemma_rate": round(unseen / n_test, 4),
            "perturbed_test_tokens": pert,
            "perturbed_rate": round(pert / n_test, 4),
            "substitutions": {f"U+{ord(k):04X}": f"U+{ord(v):04X}" for k, v in SUBST[lang].items()},
            "budget_sizes": {k: len(v) for k, v in budgets.items()},
            "upos_tags": sorted({u for s in splits["train"] for u in s["upos"]}),
        }
        (out / "stats.json").write_text(json.dumps(stats, indent=1, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
