# sdnorm (pip package `sindhinorm`): a corpus-guided, native-validated Sindhi spelling normalizer

**What it is.** A small, dependency-free tool that cleans Sindhi text typed with mixed
keyboards: Farsi yeh ی and alef maksura ى for ي, Urdu heh-goal ہ and do-chashmi ھ for ه,
keheh ک or Arabic kaf ك for ڪ, and stray zero-width characters. It is the practical output
of this project's findings: spelling variation in Sindhi text is about 30× more common than
ZWNJ, character-blind models break on it, and a native reviewer could say which variants are
safe to merge.

**Why a new tool.** Existing tools either target Urdu (urduhack's character normalization,
`urdunorm`) or convert legacy Sindhi fonts to Unicode. None handles the Sindhi-specific
problem: ک and ڪ are *both* Sindhi letters (کي "to" vs ڪي "some"), so a fixed character map
either misses variants or corrupts real words. sdnorm decides per word, using corpus
frequencies, and never merges a pair a native speaker judged different.

## Usage

The normalizer is packaged as **`sindhinorm`** (`packages/sindhinorm/`; code MIT, bundled word
list CC BY-SA 4.0). `morphtok.tools.sdnorm` re-exports it, so the project's scripts and the
package run the same code.

```bash
pip install sindhinorm                      # from PyPI; in this repo: pip install -e packages/sindhinorm
sindhinorm < input.txt > output.txt
sindhinorm explain "ھن آهی کري"             # rule and corpus counts per word
sindhinorm build-lexicon corpus.txt -o my_lexicon.json.gz
```

```python
from sindhinorm import explain, normalize

normalize("هي ڪتاب آھي")  # -> "هي ڪتاب آهي"
```

The bundled lexicon is Sindhi Wikipedia 2023-11-01 (all 66,141 lines), words seen at least
twice (61,718). With it, the evaluation below gives the same restoration (94.0%) and 1.35%
instead of 1.38% clean tokens changed (`results/sdnorm/eval_sd_min2.md`).

**Browser playground** (https://arsalankaleem.me/MorphoTok-SD-UR/, rebuilt and deployed by `.github/workflows/playground.yml`
only when the parity test passes). `packages/sindhinorm/playground/` holds a JavaScript port and a
single-page playground (`build_playground.py`). `parity_test.mjs` checks the port against the
Python package: 0 mismatches on 139,762 words (every lexicon word and keyboard-substituted
variants) and 3,000 random texts with zero-width characters and punctuation.

## Rules (fixed before evaluation)

1. NFC; ZWNJ/ZWJ removed unless a ZWNJ sits directly between two letters (native review:
   those mark compound and ال-name joins; the rest were stray).
2. Candidate spellings = all combinations of look-alike letters at the word's yeh/heh/kaf
   positions; canonical = the most frequent candidate in the lexicon.
3. Encoding-only differences (ي/ی/ى, ه/ھ/ہ): merged whenever the candidate is more frequent.
4. Lexical differences (any position involving ک, ڪ, ك or ے): merged only if the rare form
   occurs ≤ 100 times **and** the candidate is ≥ 50× more frequent.
5. 24 pairs judged DIFFERENT or UNSURE by the native reviewer are never merged.
6. Unknown words: only ی ى → ي and ہ → ه.

## Evaluation (`python scripts/12_sdnorm_eval.py` → `results/sdnorm/eval_sd.md`)

Lexicon: Sindhi Wikipedia, 3.53M word tokens.

| Test | Result |
|---|---|
| Native agreement, frequency rule alone (keep-list off), 150 pairs | merges 125/126 SAME pairs (recall 0.99) but also 18/24 DIFFERENT/UNSURE pairs: precision 0.87, specificity 0.25 |
| Confusable spelling perturbation (ي → ی) on the UD Sindhi POS test, news domain | **94.0%** of 4,511 perturbed tokens restored to the clean (normalized) form |
| Random-letter control, same tokens | 0.4% "restored" (the tool does not undo arbitrary edits) |
| Clean UD test tokens changed | 1.38% |
| Sindhi Wikipedia pilot (5,000 lines) | 4.88% of word tokens changed; word types −4.45% |

**Honest reading.**
* The rule is strong where variation is an encoding artefact and weak where it is lexical:
  frequency alone cannot tell that a rare spelling (کري, 14 times) is a different word from a
  frequent one (ڪري, 19,632). The native keep-list fixes the 24 reviewed cases only; pairs
  nobody reviewed carry the same risk, at roughly the rule's 0.87 merge precision on reviewed
  pairs.
* Most changed Wikipedia tokens are ھ → ه merges of frequent words (ھن → هن, ھي → هي). The
  reviewer judged these SAME, but some writers prefer ھ; the canonical choice follows the
  corpus majority, not a standard.
* Restoration was measured, but tagger accuracy *after* normalization was not; restoring
  94% of perturbed tokens predicts that a word-level model regains most of its confusable
  drop, which remains to be run.
* One reviewer; Sindhi only (no Urdu mode).

## Version 0.2.0: keyboard mode (2026-11-22)

**What prompted it.** On SiPOS (Ali et al., 2021), 293,683 tokens of clean Sindhi news with no
Farsi yeh, heh goal or Arabic kaf at all, the 0.1.0 rules changed 1,150 tokens (0.39%). Many of
those changes were wrong. The rules follow Wikipedia's majority spelling, so they wrote non-Sindhi
letters into correct words (عبدالقدير → عبدالقدیر, ڇونه → ڇونہ), swapped between the two heh
shapes Sindhi uses (شهر → شھر, 360 times), and once merged two real words (لڪيل "hidden" →
لکيل "written"). `scripts/sipos_inspect.py` lists them.

**Rules.** Keyboard mode (now the default) rewrites only the letters that Urdu, Persian or Arabic
keyboards produce instead of Sindhi ones (ی ى ے → ي, ہ → ه or ھ, ك → ڪ or ک) and never writes
them into a word. Where there is a choice of Sindhi letter, the more frequent spelling wins. The
guarded ک → ڪ merge keeps its thresholds (typed form ≤ 100 times, other form ≥ 50× more
frequent). A word in Sindhi letters is otherwise left alone; `fold_heh=True` restores the ه/ھ
merge. `mode="frequency"` reproduces 0.1.0 exactly. The native keep-list applies in both modes.

**Evaluation** (`python scripts/12_sdnorm_eval.py --min-count 2 --mode keyboard [--fold-heh]`,
bundled word list; `results/sdnorm/eval_sd_min2_keyboard*.md`):

| Test | 0.1.0 rules | 0.2.0 keyboard | 0.2.0 + fold_heh |
|---|---|---|---|
| UD test, ي typed as ی: restored to the normalized clean token | 94.0% | **94.9%** | 94.8% |
| … restored to the exact original token | 92.3% | **94.9%** | 93.2% |
| Random-letter control "restored" | 0.4% | 0.3% | 0.4% |
| Clean UD test tokens changed | 1.35% | **0.03%** | 1.35% |
| Clean SiPOS tokens changed | 0.39% | **0.002%** (7 tokens) | 0.36% |
| Sindhi Wikipedia pilot tokens changed | 4.92% | 0.55% | 4.98% |
| 150 native pairs, frequency rule alone: precision / recall | 0.874 / 0.992 | 0.831 / 0.508 | 0.875 / 1.000 |

Recall on the native pairs is lower in plain keyboard mode by design: most of the pairs the
reviewer judged SAME differ only in heh shape, which keyboard mode leaves alone. Of the 7 SiPOS
tokens keyboard mode still changes, 4 are چکي → چڪي, a ک → ڪ merge where both spellings may be real
words; it is a candidate for native review. The SiPOS observations motivated the design, so the
SiPOS rows are not an independent test of it; the UD rows and the preregistered tagging study
(PREREG §12) are. The browser port matches Python in all three configurations (0 mismatches on
139,762 words and 3,000 texts each).
