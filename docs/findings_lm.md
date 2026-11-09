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

The natural follow-up is the same study on the full-corpus tokenizers and text
(`PREREG.md` §10), where the LM would no longer be data-limited. It would need its own
amendment before running.

## Provenance

* Downloaded `lm-results.zip` sha256 `ebca9089…4b4cd4`; its `lm_gate5.py` is identical to
  `scripts/lm_gate5.py` (compared after normalizing line endings and the final newline).
* `results_lm_sd.jsonl` sha256 `0fd8011a…dddaa`, `results_lm_ur.jsonl` `58d7c2ae…3c8`;
  18 unique runs each, device `cuda`. Mixed-precision loss-scale reductions ("skipped
  steps"): 14 (sd) and 15 (ur) across all runs, ≤ 1 per run on average.
