"""Evaluate sdnorm (Sindhi normalizer) against native judgements and the POS perturbation test.

1. Native agreement: for each reviewed letter-variant pair, does the frequency rule (with the
   native keep-list *disabled*, so this is not circular) rewrite B as A? Compared with the
   reviewer's SAME vs DIFFERENT/UNSURE.
2. Spelling restoration on the UD Sindhi POS test (news domain, out of the Wikipedia lexicon's
   domain): share of confusable-perturbed tokens mapped back to their clean form, the same for
   the random-letter control, and the share of clean tokens the tool changes.
3. Corpus effect on the 5,000-line Wikipedia pilot: word tokens changed, types merged.

Writes ``results/sdnorm/eval_sd.md`` (metric-only). Needs the git-ignored review sheet and
corpora; see data/raw/SOURCE.md.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from morphtok.tools.sdnorm import Normalizer, build_lexicon, tokens  # noqa: E402

LEXICON_CORPUS = ROOT / "data" / "processed" / "sd_wiki20231101_pilot66141.txt"
PILOT = ROOT / "data" / "processed" / "sd_wiki20231101_pilot5000.txt"
SHEET = ROOT / "data" / "audit" / "review" / "sd_letter_variants.tsv"
TASK = ROOT / "data" / "tasks" / "sd_pos"


def words_of(s: str) -> str:
    """The word part of a whitespace token (punctuation stripped)."""
    return "".join(w for is_w, w in tokens(s) if is_w)


def flat(path: Path) -> list[str]:
    """All tokens of a JSONL task file, in order."""
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out += json.loads(line)["tokens"]
    return out


def main() -> int:
    """Run the three evaluations."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    with LEXICON_CORPUS.open(encoding="utf-8") as f:
        lex = build_lexicon(f)
    rule = Normalizer(lex, keep=frozenset())
    full = Normalizer(lex)
    lines = ["# sdnorm evaluation (Sindhi)", "",
             f"Lexicon: {LEXICON_CORPUS.name} ({sum(lex.values()):,} word tokens, {len(lex):,} types). "
             "Thresholds fixed before evaluation: lex_ratio = 50, lex_max_count = 100.", ""]  # fmt: skip

    # 1. native agreement
    rows = SHEET.read_text(encoding="utf-8-sig").splitlines()
    h = rows[0].split("\t")
    ix = {k: i for i, k in enumerate(h)}
    conf: Counter[tuple[str, str]] = Counter()
    misses: list[str] = []
    for r in rows[1:]:
        x = r.split("\t")
        a = words_of(x[ix["spelling_A (count)"]].rsplit(" (", 1)[0])
        b = words_of(x[ix["spelling_B (count)"]].rsplit(" (", 1)[0])
        native = "SAME" if x[ix["decision"]].strip().upper() == "SAME" else "KEEP"
        tool = "SAME" if rule.normalize_word(b) == rule.normalize_word(a) else "KEEP"
        conf[(native, tool)] += 1
        if native != tool:
            misses.append(f"{x[ix['pair_id']]}: {a} / {b} native {native}, rule {tool}")
    tp, fp = conf[("SAME", "SAME")], conf[("KEEP", "SAME")]
    fn, tn = conf[("SAME", "KEEP")], conf[("KEEP", "KEEP")]
    lines += ["## 1. Agreement with native judgements (150 pairs; keep-list disabled)", "",
              "| | rule merges | rule keeps apart |", "|---|---|---|",
              f"| native SAME | {tp} | {fn} |", f"| native DIFFERENT/UNSURE | {fp} | {tn} |", "",
              f"Merge precision {tp / max(1, tp + fp):.3f}, recall {tp / max(1, tp + fn):.3f}, "
              f"accuracy {(tp + tn) / max(1, sum(conf.values())):.3f}. With the keep-list enabled "
              "the DIFFERENT/UNSURE pairs are never merged by construction.", "",
              "Disagreements:", ""] + [f"* {m}" for m in misses] + [""]  # fmt: skip

    # 2. restoration on the POS test
    clean = flat(TASK / "test.jsonl")
    pert = flat(TASK / "test_confusable.jsonl")
    noise = flat(TASK / "test_randnoise.jsonl")
    changed = [i for i, (c, p) in enumerate(zip(clean, pert, strict=True)) if c != p]
    nchanged = [i for i, (c, p) in enumerate(zip(clean, noise, strict=True)) if c != p]
    restored = sum(full.normalize(pert[i]) == full.normalize(clean[i]) for i in changed)
    restored_raw = sum(full.normalize(pert[i]) == clean[i] for i in changed)
    n_restored = sum(full.normalize(noise[i]) == full.normalize(clean[i]) for i in nchanged)
    touched = sum(full.normalize(t) != t for t in clean)
    lines += ["## 2. Spelling restoration on the UD Sindhi POS test (news domain)", "",
              f"* Confusable-perturbed tokens (ي → ی): {len(changed):,}. After sdnorm, identical to the "
              f"normalized clean token: **{restored / len(changed):.3f}**; identical to the original clean "
              f"token: {restored_raw / len(changed):.3f}.",
              f"* Random-letter control: {len(nchanged):,} tokens; restored {n_restored / len(nchanged):.3f} "
              "(expected near 0: the tool should not undo arbitrary edits).",
              f"* Clean test tokens changed by sdnorm: {touched:,} of {len(clean):,} ({touched / len(clean):.3%}).",
              ""]  # fmt: skip

    # 3. corpus effect
    tot = chg = 0
    before: Counter[str] = Counter()
    after: Counter[str] = Counter()
    for ln in PILOT.read_text(encoding="utf-8").splitlines():
        for is_w, w in tokens(ln):
            if not is_w:
                continue
            o = full.normalize_word(w)
            tot += 1
            chg += o != w
            before[w] += 1
            after[o] += 1
    lines += ["## 3. Effect on the 5,000-line Sindhi Wikipedia pilot", "",
              f"* Word tokens changed: {chg:,} of {tot:,} ({chg / tot:.2%}).",
              f"* Word types: {len(before):,} → {len(after):,} ({(len(after) - len(before)) / len(before):+.2%}).",
              ""]  # fmt: skip
    text = "\n".join(lines)
    print(text)
    dest = ROOT / "results" / "sdnorm"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "eval_sd.md").write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
