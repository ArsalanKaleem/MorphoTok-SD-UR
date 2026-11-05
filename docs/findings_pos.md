# POS study findings (combined plan), exploratory

**Status (2026-11-05).** CPU-scale pilot: BiLSTM taggers trained from scratch, **not**
XLM-R (`scripts/xlmr_fusion.py` is written but has not run). Official UD test sets, dev
used only for early stopping. Paired, seed-matched deltas with 95% t-intervals over seeds
(5 seeds at the 1% and 10% budgets, 3 at 100%). Full tables: `runs/SD-POS-report.md`,
`runs/UR-POS-report.md` (`python scripts/08_pos_report.py --lang sd|ur`). The
preregistration is not frozen; treat everything here as pilot evidence.

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

## Interpretation (Sindhi; Urdu where stated, provisional)

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
