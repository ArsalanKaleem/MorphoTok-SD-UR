# Gate 5 language-model results (sd)

18 runs. Bits per character (lower is better), mean ± sd over seeds.

| tokenizer | V | test bpc | held-out-lemma bpc | unseen-form bpc | tokens/char | steps |
|---|---|---|---|---|---|---|
| unigram | 4000 | 1.9013 ± 0.0378 | 1.4660 ± 0.0221 | 3.8358 ± 0.0514 | 0.526 | 6000 |
| unigram_hard_trainonly | 4000 | 1.8970 ± 0.0415 | 1.4662 ± 0.0223 | 3.8126 ± 0.0665 | 0.535 | 6000 |
| unigram | 8000 | 1.8544 ± 0.0222 | 1.4234 ± 0.0163 | 3.8345 ± 0.0218 | 0.489 | 6000 |
| unigram_hard_trainonly | 8000 | 1.8639 ± 0.0064 | 1.4317 ± 0.0059 | 3.8365 ± 0.0094 | 0.500 | 6000 |
| unigram | 16000 | 1.8214 ± 0.0085 | 1.4014 ± 0.0080 | 3.8610 ± 0.0055 | 0.467 | 6000 |
| unigram_hard_trainonly | 16000 | 1.8304 ± 0.0082 | 1.4075 ± 0.0047 | 3.8804 ± 0.0080 | 0.479 | 6000 |

## Paired contrasts (Δbpc = system − reference; 95% t-interval over seeds)

| contrast | V | text | Δbpc | 95% CI | verdict (§9 rule) |
|---|---|---|---|---|---|
| `unigram_hard_trainonly − unigram` (primary) | 4000 | all test text | -0.0043 | [-0.2010, +0.1924] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 4000 | held-out-lemma words | +0.0002 | [-0.1094, +0.1098] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 4000 | forms unseen in LM training | -0.0232 | [-0.3158, +0.2694] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 4000 | seen forms | -0.0030 | [-0.1931, +0.1872] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` (primary) | 8000 | all test text | +0.0095 | [-0.0518, +0.0709] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 8000 | held-out-lemma words | +0.0083 | [-0.0320, +0.0485] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 8000 | forms unseen in LM training | +0.0020 | [-0.0748, +0.0788] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 8000 | seen forms | +0.0101 | [-0.0503, +0.0704] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` (primary) | 16000 | all test text | +0.0090 | [-0.0158, +0.0338] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 16000 | held-out-lemma words | +0.0061 | [-0.0111, +0.0233] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 16000 | forms unseen in LM training | +0.0194 | [-0.0058, +0.0447] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 16000 | seen forms | +0.0082 | [-0.0165, +0.0330] | no detectable effect (n=3) |
