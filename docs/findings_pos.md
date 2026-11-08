# POS study findings (combined plan), exploratory

**Status (2026-11-08).** Two model families on the official UD test sets (dev used only for
early stopping), with paired, seed-matched deltas and 95% t-intervals over seeds:

1. **CPU pilot:** BiLSTM taggers trained from scratch (5 seeds at 1% and 10%, 3 at 100%).
   Tables: `runs/SD-POS-report.md`, `runs/UR-POS-report.md` (`scripts/08_pos_report.py`).
2. **XLM-R base** fine-tuned on a Kaggle T4, with and without character fusion (3 seeds).
   Tables: `results/xlmr_kaggle/report_{sd,ur}.md` (`scripts/09_xlmr_report.py`). See the
   section **"With a pretrained encoder (XLM-R)"**, which revises the CPU interpretation.

The preregistration is not frozen; treat everything here as pilot evidence.

## Headline (both model families, both languages)

**Character information buys robustness to spelling perturbation in every setting. It
improves generalization to unseen lemmas only for models trained from scratch; with a
pretrained encoder (XLM-R) it gives no gain there, and at the 1% budget it costs accuracy.**
Aggregate accuracy hides both effects.

## Question

Where should morphological information enter: the **tokenizer** (a Unigram vocabulary
learned with boundary supervision from UD *train* lemmas only, "hard train-only") or the
**model input** (character CNN fused with subword embeddings)? And does it buy
**morphological generalization** (tokens whose lemma never appears in training) or only
**spelling robustness** (confusable code-point substitution; random-letter control)?

## Sindhi (UD Sindhi-Isra; 74.6k train tokens; 11.1k test tokens)

### Full training set (3 seeds)

| System | All | Unseen lemma (795 tok.) | Δ unseen vs `word` [95% CI] |
|---|---|---|---|
| `word` (whole-word embeddings) | 0.909 | 0.570 | — |
| `sub:bpe` | 0.912 | 0.636 | +0.066 [+0.016, +0.117] |
| `sub:unigram` | 0.909 | 0.606 | +0.036 [−0.012, +0.085] |
| `sub:unigram_hard_trainonly` | 0.910 | 0.618 | +0.049 [−0.010, +0.107] |
| `char` | 0.912 | 0.596 | +0.026 [−0.053, +0.106] |
| `concat:unigram` | 0.921 | 0.607 | +0.037 [−0.050, +0.125] |
| `gated:unigram` | 0.921 | 0.620 | +0.050 [+0.030, +0.071] |
| **`gated:unigram_hard_trainonly`** | **0.923** | **0.646** | **+0.076 [+0.049, +0.103]** |

### The two contrasts that answer the question

**(a) Tokenizer-level morphology inside fusion** (`gated:hard` − `gated:unigram`, same
architecture and parameters; only the tokenizer differs):

| Budget | Δ all | Δ unseen lemma |
|---|---|---|
| 1% (41 sentences) | −0.036 [−0.159, +0.087] | **+0.020 [+0.001, +0.040]** |
| 10% (410) | +0.005 [−0.001, +0.012] | **+0.011 [+0.001, +0.020]** |
| 100% (4,096) | +0.002 [−0.006, +0.010] | **+0.026 [+0.008, +0.044]** |

Without character features, the same tokenizer change is not significant on unseen lemmas
(`sub:hard` − `sub:unigram` at 100%: +0.013 [−0.021, +0.046]).

**(b) Gate vs parameter-matched concatenation** (`gated:unigram` − `concat:unigram`):
+0.032 [+0.011, +0.053] unseen-lemma at 10%; within noise at 1% and 100%.

### Spelling robustness (accuracy drop on the ~41% of test tokens that are perturbed)

| System (100%) | Drop: confusable | Drop: random-letter control |
|---|---|---|
| `word` | 0.501 | 0.499 |
| `sub:unigram` | 0.415 | 0.451 |
| `sub:unigram_hard_trainonly` | 0.376 | 0.443 |
| `char` | 0.283 (high seed variance) | 0.358 |
| `gated:unigram_hard_trainonly` | 0.326 | 0.410 |

The whole-word model collapses under either perturbation. Character input roughly halves
the damage at the 1% and 10% budgets (e.g. 10%: drop 0.52 → 0.19 for `char`).
Confusable-substitution drops have large between-seed variance at the full budget, so
the 100% robustness CIs mostly include 0.

## Urdu (UD Urdu-UDTB; 108.7k train tokens)

### 1% and 10% budgets (all systems, 5 seeds)

| System | All 1% | Unseen lemma 1% | All 10% | Unseen lemma 10% | Drop: confusable 10% |
|---|---|---|---|---|---|
| `word` | 0.446 | 0.285 | 0.823 | 0.513 | 0.532 |
| `sub:bpe` | 0.515 | 0.410 | 0.846 | 0.596 | 0.542 |
| `sub:unigram` | 0.584 | 0.426 | 0.849 | 0.612 | 0.507 |
| `sub:unigram_hard_trainonly` | 0.639 | 0.486 | 0.851 | 0.617 | 0.557 |
| `char` | 0.680 | 0.522 | 0.859 | 0.614 | 0.334 |
| `concat:unigram` | 0.702 | 0.513 | 0.866 | 0.607 | 0.465 |
| `gated:unigram` | 0.641 | 0.502 | 0.872 | 0.636 | 0.392 |
| `gated:unigram_hard_trainonly` | 0.705 | 0.508 | 0.876 | 0.640 | 0.388 |

* **Replicates Sindhi:** the gate beats parameter-matched concatenation at 10% on unseen lemmas
  (`concat` − `gated` = −0.029 [−0.051, −0.007]), and character input drives both
  unseen-lemma and robustness gains over whole-word embeddings.
* **Does not replicate (so far):** the morph tokenizer's advantage *inside* fusion
  (`gated:hard` − `gated:unigram`): +0.006 [−0.033, +0.044] at 1%, +0.003 [−0.020, +0.027]
  at 10%. Full-budget results below.
* Urdu confusable drops are large for subword-only systems (≈0.5). The substitution touches
  47% of test tokens and Farsi yeh is very frequent, so many in-vocabulary words become OOV.

### Full training set (six key systems, 3 seeds)

| System | All | Unseen lemma (889 tok.) | Drop: confusable | Drop: noise |
|---|---|---|---|---|
| `word` | 0.920 | 0.636 | 0.635 | 0.630 |
| `sub:unigram` | 0.918 | 0.710 | 0.547 | 0.567 |
| `sub:unigram_hard_trainonly` | 0.921 | 0.715 | 0.538 | 0.561 |
| `char` | 0.917 | 0.682 | 0.251 | 0.390 |
| `gated:unigram` | 0.929 | 0.715 | 0.345 | 0.491 |
| **`gated:unigram_hard_trainonly`** | **0.929** | **0.727** | 0.360 | 0.488 |

* `gated:hard` − `gated:unigram`, unseen lemma: **+0.013 [−0.030, +0.055]**, the same direction as
  Sindhi but **not significant**. Against `sub:unigram`, only `gated:hard` gains significantly
  on unseen lemmas: +0.018 [+0.004, +0.032].
* Character input is again what buys robustness: `char` − `word` on confusable tokens
  +0.376 [+0.325, +0.428]; noise +0.232 [+0.091, +0.374].

## Cross-language summary

| Claim | Sindhi | Urdu |
|---|---|---|
| Character input (alone or fused) makes taggers far more robust to spelling perturbation | yes, all budgets | yes, all budgets |
| Gated fusion > parameter-matched concat | 10% only | 10% only |
| Morph tokenizer adds unseen-lemma accuracy **inside fusion**, vs the unsupervised Unigram | yes, all 3 budgets (CIs exclude 0) | same direction, not significant |
| … vs BPE inside fusion (`gated:bpe`) | ahead, not significant | not run |
| Best unseen-lemma system at full budget | `gated:unigram_hard_trainonly` | `gated:unigram_hard_trainonly` |
| Overall accuracy separates the systems | barely (≤1.4 points) | barely (≤1.2 points) |

## With a pretrained encoder (XLM-R base; Kaggle T4; 3 seeds)

Same task files, same diagnostic test sets. `base` = XLM-R fine-tuning; `concat` / `gated` =
XLM-R first-subword states fused with a character CNN (parameter-matched).

### Absolute accuracy (mean over seeds)

| | Budget | XLM-R `base` all / unseen lemma | Best CPU value per column (any system) all / unseen lemma |
|---|---|---|---|
| Sindhi | 1% | **0.882 / 0.789** | 0.726 / 0.539 |
| Sindhi | 100% | **0.941 / 0.769** | 0.923 / 0.646 |
| Urdu | 1% | **0.892 / 0.818** | 0.705 / 0.522 |
| Urdu | 100% | **0.946 / 0.871** | 0.929 / 0.727 |

Pretraining dominates: XLM-R alone beats every CPU system at every budget, by far the most
at 1%. (The two families are not a controlled comparison: different models and training.)
Unseen-lemma token counts differ by budget: 4,748 (1%) to 795 (100%) in Sindhi.

### Paired effect of character fusion (`gated` − `base`; mean [95% t-CI], n = 3)

| | Budget | Δ unseen lemma | Δ confusable spelling | Δ random-letter noise |
|---|---|---|---|---|
| Sindhi | 1% | **−0.041 [−0.050, −0.031]** | **+0.107 [+0.024, +0.190]** | +0.063 [−0.045, +0.170] |
| Sindhi | 10% | −0.007 [−0.030, +0.016] | +0.059 [−0.026, +0.144] | +0.033 [−0.012, +0.078] |
| Sindhi | 100% | +0.003 [−0.018, +0.023] | +0.048 [−0.043, +0.138] | +0.033 [−0.003, +0.068] |
| Urdu | 1% | −0.008 [−0.022, +0.005] | **+0.029 [+0.013, +0.045]** | **+0.042 [+0.020, +0.064]** |
| Urdu | 10% | +0.003 [−0.006, +0.012] | +0.002 [−0.047, +0.051] | +0.018 [−0.036, +0.071] |
| Urdu | 100% | −0.003 [−0.047, +0.040] | +0.022 [−0.015, +0.058] | **+0.058 [+0.017, +0.098]** |

`concat` − `base` shows the same pattern with tighter intervals for robustness: Sindhi
confusable +0.077 [+0.017, +0.137] (1%), +0.055 [+0.023, +0.088] (10%), +0.050 [+0.010,
+0.091] (100%); Urdu noise +0.034 [+0.026, +0.042] (10%), +0.023 [+0.014, +0.032] (100%).
`concat` also lowers unseen-lemma accuracy at 1% (Sindhi −0.034, Urdu −0.019; CIs exclude 0).

**Gate vs concat:** no robustness difference. Small unseen-lemma edge for the gate in two
cells (Sindhi 10%: +0.013 [+0.002, +0.025]; Urdu 1%: +0.011 [+0.008, +0.014]).

### What this changes

* **C1 (character fusion improves unseen-lemma accuracy):** holds for from-scratch taggers
  and **fails for XLM-R**: no gain at 10% or 100%, and a loss at 1% (Sindhi significant).
  A pretrained subword encoder already generalizes well to unseen lemmas (0.77–0.87), and
  adding a randomly initialized character branch with very little labelled data appears to
  dilute it.
* **C2 (character input buys spelling robustness):** holds for **both** model families and
  both languages, smaller with XLM-R (confusable gains +0.02 to +0.11 vs +0.2 to +0.4 for the
  CPU taggers).
* **C4 (gate > concat):** not supported for XLM-R beyond two small unseen-lemma cells.
* XLM-R `base` itself is far less hurt by the *confusable* substitution than by random
  letters (Sindhi drop 0.29 vs 0.41; Urdu 0.14 vs 0.35), consistent with pretraining having
  seen both yeh variants. That supports treating the substitution as a realistic variant;
  native approval (review Task 3) is still pending.
* The tokenizer-level comparison (C5) was not run with XLM-R, whose tokenizer is fixed.

## Interpretation of the CPU pilot (Sindhi; Urdu where stated; revised by the XLM-R section)

1. **Morphological generalization and spelling robustness come from different places.**
   Character input does most for robustness, and the gain is largest with little data.
   The *tokenizer's* morphology adds unseen-lemma accuracy consistently, but **only in
   combination with character features**. The two are complementary, not substitutes
   (hypothesis C5).
2. **Overall accuracy hides this.** All non-baseline systems are within ~1.4 points of each
   other on all tokens at 100%, while unseen-lemma accuracy differs by up to 7.6 points.
   Reporting aggregate POS accuracy alone (as is standard) would miss the effect.
3. **The gate helps a little, at mid budget only** (C4: partially supported). It is not the
   source of the main effect, so it should not be the paper's headline. This matches the
   novelty screen: character + word fusion for Sindhi POS already exists (the SiPOS
   baselines).
4. **Intrinsic segmentation quality does not predict tagging.** Among subword-only
   systems, `sub:bpe` has the best unseen-lemma accuracy at 100% (0.636, vs 0.606 for
   `sub:unigram`), although Unigram segmented unseen lemmas better intrinsically in the
   tokenizer pilot (`docs/findings_pilot.md`).
   **Control run afterwards (`gated:bpe`, Sindhi, same budgets and seeds):** inside fusion the
   morph tokenizer is ahead of BPE on unseen lemmas at every budget, but not significantly:
   +0.031 [−0.009, +0.071] at 1%, +0.005 [−0.000, +0.010] at 10%, +0.016 [−0.073, +0.105] at
   100%. `gated:bpe` ≈ `gated:unigram`. **So the supported claim is narrower:** morph supervision
   beats the *same* Unigram tokenizer without supervision (Sindhi, all budgets); that it beats
   BPE is not established.
5. **Absolute accuracy is far below the state of the art** (Stanza + MuRIL: UPOS F1 98.44 on
   this treebank, Bauer et al. 2025), as expected for small from-scratch taggers. Whether
   the *pattern* survives a pretrained encoder is the XLM-R experiment's job.

## Caveats

* Single tokenizer seed. Tagger seeds carry the reported variance.
* `test_confusable` is a hypothesis about equivalent spellings until native review (Task 3).
  It also edits every occurrence of the letter, whereas the control edits one letter.
* Unseen-lemma counts are small at 100% (795 tokens), hence the wide CIs.
* UD lemmas define "unseen lemma". Lemmatization conventions affect the subset.
