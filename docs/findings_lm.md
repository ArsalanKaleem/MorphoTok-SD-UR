# Gate 5: does the tokenizer gain transfer to language modelling? (H7)

Preregistered in `PREREG.md` §9 (Amendment 2, tag `prereg-v3`) before any run. Run on a
Kaggle T4 on 2026-11-09; analysed with `scripts/15_lm_report.py`. Full tables:
[`results/lm_kaggle/report_lm_sd.md`](../results/lm_kaggle/report_lm_sd.md),
[`results/lm_kaggle/report_lm_ur.md`](../results/lm_kaggle/report_lm_ur.md).

## Setup (as preregistered)

36 small transformer LMs (4.25M parameters, 4 layers, d = 256), one per language ×
tokenizer (`unigram`, `unigram_hard_trainonly`, `bpe`) × V ∈ {2000, 4000} × seed {0, 1, 2},
trained on the 5,000-line Wikipedia pilot, early-stopped on dev, scored once on test in
bits per character (bpc; the same characters for every tokenizer).

## Primary result: no transfer

`unigram_hard_trainonly − unigram`, test bpc (negative = better LM), mean and 95%
t-interval over 3 seeds:

| lang | V | Δbpc | 95% CI | verdict |
|---|---|---|---|---|
| sd | 2000 | +0.0026 | [−0.0137, +0.0190] | no detectable effect |
| sd | 4000 | −0.0014 | [−0.1282, +0.1253] | no detectable effect |
| ur | 2000 | +0.0102 | [+0.0052, +0.0152] | **harm** (+0.45%) |
| ur | 4000 | −0.0073 | [−0.0364, +0.0218] | no detectable effect |

The tokenizer that segments morphology better (preregistered intrinsic gain, 3 of 4 tests)
gives no better language model in any cell, and a slightly worse one in one cell. This
matches the recorded prediction (the token-bigram proxy was 0.2–0.6% worse).

**Secondary.** On words of held-out lemmas, the place a transfer should show first, the
direction is favourable in 3 of 4 cells (sd −0.008, −0.010; ur +0.009, −0.012 bpc) but no
interval excludes 0. `bpe − unigram` has no cell with an interval excluding 0 in
`bpe`'s favour and 3 cells where `bpe` is worse with the interval excluding 0. With 16 secondary contrasts per language, the single favourable
"transfer" cell (ur V4000, seen forms, −0.011) is not interpreted.

## Caveats (fixed in §9 before the run, plus one observed)

* **Data-limited LMs (observed).** Every run reached its best dev bpc at 1,000–1,250
  steps and then overfit; early stopping kept the best checkpoint, and runs stopped at
  2,250–2,500 of the allowed 6,000 steps. The models are limited by the 5,000-line corpus,
  not by the step budget. Between-seed spread in Sindhi (sd ≈ 0.03 bpc) is larger than the
  effects being tested, so the Sindhi intervals are wide: "no detectable effect" there
  does not rule out effects of a few hundredths of a bit.
* One small LM size, one domain (Wikipedia), 3 seeds.

The natural follow-up, the same study with LMs that are not data-limited, was preregistered
as `PREREG.md` §11 and run; see the next section.

## Full-corpus study (PREREG.md §11, Amendment 6, tag `prereg-v7`)

Same LM, recipe and decision rule as above, on the full-corpus tokenizers of §10
(`unigram`, `unigram_hard_trainonly`; V = 4000, 8000, 16000; 3 seeds), 18 LMs per language.
Training text: Sindhi all 53,036 train lines, Urdu a seeded 150,000 lines (≈ 10–30× the
pilot); dev 5,000 lines; test 6,573 (sd) and 20,000 (ur) lines. Kaggle T4, 2026-11-10.
Tables: [`results/lm_full_kaggle/report_lm_sd.md`](../results/lm_full_kaggle/report_lm_sd.md),
[`results/lm_full_kaggle/report_lm_ur.md`](../results/lm_full_kaggle/report_lm_ur.md).

**Primary result: no detectable effect in all 6 cells.** `unigram_hard_trainonly − unigram`,
test bpc, mean and 95% t-interval over 3 seeds:

| lang | V | Δbpc | 95% CI |
|---|---|---|---|
| sd | 4000 | −0.004 | [−0.201, +0.192] |
| sd | 8000 | +0.010 | [−0.052, +0.071] |
| sd | 16000 | +0.009 | [−0.016, +0.034] |
| ur | 4000 | −0.003 | [−0.033, +0.028] |
| ur | 8000 | +0.016 | [−0.024, +0.056] |
| ur | 16000 | +0.017 | [−0.013, +0.047] |

* No cell shows transfer, and no cell shows harm (the pilot's small Urdu V = 2000 harm does
  not reappear; V = 2000 was not part of §11). Point estimates are near zero at V = 4000
  and slightly unfavourable (+0.5–1.1%) at V = 8000 and 16000, none significant.
* **Held-out-lemma words** (where a transfer should show first): no interval excludes 0;
  point estimates −0.004 to +0.013 bpc. The prediction recorded in §11 (no transfer on all
  text) holds, and the hoped-for held-out-lemma benefit does not appear.
* **No longer data-limited (secondary check).** No run overfit: the best dev bpc came at
  the last or second-to-last evaluation (17/18 runs per language at the last). Test bpc
  fell by about half a bit compared with the pilot (`unigram` V = 4000: sd 2.388 → 1.901,
  ur 2.249 → 1.712). Runs were mildly step-limited: dev bpc was still falling by about
  0.006–0.007 bpc (≈ 0.4%) over the final 1,000 of 6,000 steps.
* Seed-to-seed variation is large relative to the effects (per-seed deltas change sign in
  every cell; Sindhi V = 4000 ranges from −0.088 to +0.069). The intervals span about
  ±0.03–0.06 bpc in five cells and ±0.20 in Sindhi V = 4000, so smaller effects are not
  ruled out.

**Reading.** Across both studies, 10 preregistered cells and 72 language models, the
tokenizer that segments morphology better (a gain that replicates at full scale, §10)
never gives a detectably better language model. The intrinsic gain does not transfer to
language modelling at this model size (3.7–7.3M parameters, ≤ 6,000 steps), in either
language.

## Provenance

* Downloaded `lm-results.zip` sha256 `ebca9089…4b4cd4`; its `lm_gate5.py` is identical to
  `scripts/lm_gate5.py` (compared after normalizing line endings and the final newline).
* `results_lm_sd.jsonl` sha256 `0fd8011a…dddaa`, `results_lm_ur.jsonl` `58d7c2ae…3c8`;
  18 unique runs each, device `cuda`. Mixed-precision loss-scale reductions ("skipped
  steps"): 14 (sd) and 15 (ur) across all runs, ≤ 1 per run on average.
* Full-corpus study: downloaded `results (1).zip` (sd) sha256 `f93fb730…a051f2` and
  `results.zip` (ur) `6c3a1806…048c93`; each contains an `lm_gate5.py` identical to the
  repository copy. `results_lm_sd.jsonl` `6d20e97c…eb3588`, `results_lm_ur.jsonl`
  `b7045008…5f4c10`; 18 unique runs each, device `cuda`, 6,000 steps each, and every run's
  test tokens/char equals that of the exported stream it names (`data/tasks/lm_full`).
  Loss-scale reductions: 18 (sd) and 13 (ur) across all runs.
