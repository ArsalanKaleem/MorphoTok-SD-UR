# Gate 5 language-model results (ur)

18 runs. Bits per character (lower is better), mean ± sd over seeds.

| tokenizer | V | test bpc | held-out-lemma bpc | unseen-form bpc | tokens/char | steps |
|---|---|---|---|---|---|---|
| unigram | 4000 | 1.7123 ± 0.0032 | 1.4068 ± 0.0023 | 3.7472 ± 0.0003 | 0.579 | 6000 |
| unigram_hard_trainonly | 4000 | 1.7098 ± 0.0097 | 1.4033 ± 0.0085 | 3.7455 ± 0.0122 | 0.582 | 6000 |
| unigram | 8000 | 1.6330 ± 0.0055 | 1.3179 ± 0.0038 | 3.7155 ± 0.0109 | 0.488 | 6000 |
| unigram_hard_trainonly | 8000 | 1.6492 ± 0.0119 | 1.3263 ± 0.0066 | 3.7597 ± 0.0257 | 0.494 | 6000 |
| unigram | 16000 | 1.6148 ± 0.0150 | 1.2940 ± 0.0120 | 3.7991 ± 0.0196 | 0.462 | 6000 |
| unigram_hard_trainonly | 16000 | 1.6321 ± 0.0192 | 1.3074 ± 0.0173 | 3.8295 ± 0.0261 | 0.469 | 6000 |

## Paired contrasts (Δbpc = system − reference; 95% t-interval over seeds)

| contrast | V | text | Δbpc | 95% CI | verdict (§9 rule) |
|---|---|---|---|---|---|
| `unigram_hard_trainonly − unigram` (primary) | 4000 | all test text | -0.0026 | [-0.0327, +0.0276] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 4000 | held-out-lemma words | -0.0036 | [-0.0294, +0.0223] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 4000 | forms unseen in LM training | -0.0016 | [-0.0312, +0.0280] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 4000 | seen forms | -0.0026 | [-0.0328, +0.0276] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` (primary) | 8000 | all test text | +0.0162 | [-0.0238, +0.0562] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 8000 | held-out-lemma words | +0.0084 | [-0.0161, +0.0329] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 8000 | forms unseen in LM training | +0.0442 | [-0.0340, +0.1224] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 8000 | seen forms | +0.0146 | [-0.0232, +0.0524] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` (primary) | 16000 | all test text | +0.0173 | [-0.0129, +0.0474] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 16000 | held-out-lemma words | +0.0134 | [-0.0114, +0.0382] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 16000 | forms unseen in LM training | +0.0304 | [-0.0085, +0.0694] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 16000 | seen forms | +0.0165 | [-0.0131, +0.0461] | no detectable effect (n=3) |
