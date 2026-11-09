# Full-corpus scale-up (H5; PREREG.md §10)

Preregistered in Amendment 3 (tag `prereg-v4`) before any full-corpus run. Trained on CPU
on 2026-11-09 with `scripts/03_train_tokenizers.py --config configs/run/scale_full.yaml`,
evaluated with `scripts/16_scale_eval.py`. Reports:
[`results/scale_full/report_sd.md`](../results/scale_full/report_sd.md),
[`results/scale_full/report_ur.md`](../results/scale_full/report_ur.md).

**Question.** Does the confirmed gain of train-only boundary supervision
(`unigram_hard_trainonly − unigram`) survive when tokenizers are trained on full
Wikipedia instead of the 5,000-line pilot (about 13× more Sindhi lines, 170× more Urdu lines)?

**Answer: yes, in all 6 preregistered cells.**

| lang | train lines | V | ΔF1 dev silver (primary) [95% t-CI] | Δ tokens/word | verdict |
|---|---|---|---|---|---|
| sd | 53,036 | 4000 | +0.030 [+0.019, +0.041] | +2.9% | replicates |
| sd | 53,036 | 8000 | +0.035 [+0.029, +0.040] | +3.9% | replicates |
| sd | 53,036 | 16000 | +0.051 [+0.029, +0.072] | +4.8% | replicates |
| ur | 683,201 | 4000 | +0.016 [+0.015, +0.017] | +1.0% | replicates |
| ur | 683,201 | 8000 | +0.017 [+0.013, +0.021] | +2.2% | replicates |
| ur | 683,201 | 16000 | +0.020 [+0.017, +0.024] | +2.9% | replicates |

**Secondary.**
* Every one of the 45 per-seed deltas (both languages, all V, every gold) is positive.
* Sindhi, 267 native-reviewed dev words: +0.026, +0.030, +0.030 (V = 4000, 8000, 16000),
  every interval excluding 0. At pilot scale the native-gold gain held at V = 4000 only.
* Test silver (non-confirmatory, already used once): +0.010 to +0.049, every interval
  excluding 0.

**The recorded prediction** ("replicates at every V in Sindhi; smaller in Urdu") was
correct on both points: the Urdu gain is about half the Sindhi gain.

**Caveats.**
* Silver gold, except the 267 Sindhi native words. Wikipedia only.
* Sindhi V = 16000 costs +4.8% tokens/word, close to the 5% limit.
* Gold covers lemmas with UD/UniMorph analyses (dev 961 sd / 1,618 ur types), not the
  whole vocabulary.
* Fertility comes from a seeded sample of 5,000 dev lines, fixed in §10.
