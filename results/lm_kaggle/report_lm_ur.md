# Gate 5 language-model results (ur)

18 runs. Bits per character (lower is better), mean ± sd over seeds.

| tokenizer | V | test bpc | held-out-lemma bpc | unseen-form bpc | tokens/char | steps |
|---|---|---|---|---|---|---|
| bpe | 2000 | 2.2919 ± 0.0090 | 1.8573 ± 0.0146 | 4.3423 ± 0.0181 | 0.550 | 2250 |
| unigram | 2000 | 2.2602 ± 0.0068 | 1.8300 ± 0.0121 | 4.2375 ± 0.0089 | 0.552 | 2250 |
| unigram_hard_trainonly | 2000 | 2.2704 ± 0.0051 | 1.8392 ± 0.0101 | 4.2283 ± 0.0240 | 0.556 | 2250 |
| bpe | 4000 | 2.3025 ± 0.0280 | 1.8410 ± 0.0189 | 4.4058 ± 0.0228 | 0.507 | 2250 |
| unigram | 4000 | 2.2493 ± 0.0070 | 1.8180 ± 0.0066 | 4.2970 ± 0.0616 | 0.509 | 2250 |
| unigram_hard_trainonly | 4000 | 2.2420 ± 0.0058 | 1.8058 ± 0.0052 | 4.3078 ± 0.0261 | 0.513 | 2250 |

## Paired contrasts (Δbpc = system − reference; 95% t-interval over seeds)

| contrast | V | text | Δbpc | 95% CI | verdict (§9 rule) |
|---|---|---|---|---|---|
| `unigram_hard_trainonly − unigram` (primary) | 2000 | all test text | +0.0102 | [+0.0052, +0.0152] | **harm** (worse LM) (n=3) |
| `unigram_hard_trainonly − unigram` | 2000 | held-out-lemma words | +0.0092 | [-0.0097, +0.0281] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 2000 | forms unseen in LM training | -0.0092 | [-0.0485, +0.0301] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 2000 | seen forms | +0.0137 | [+0.0081, +0.0194] | **harm** (worse LM) (n=3) |
| `unigram_hard_trainonly − unigram` (primary) | 4000 | all test text | -0.0073 | [-0.0364, +0.0218] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 4000 | held-out-lemma words | -0.0122 | [-0.0322, +0.0077] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 4000 | forms unseen in LM training | +0.0108 | [-0.2037, +0.2252] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 4000 | seen forms | -0.0107 | [-0.0192, -0.0021] | **transfer** (better LM) (n=3) |
| `bpe − unigram` | 2000 | all test text | +0.0317 | [+0.0013, +0.0622] | **harm** (worse LM) (n=3) |
| `bpe − unigram` | 2000 | held-out-lemma words | +0.0273 | [-0.0298, +0.0844] | no detectable effect (n=3) |
| `bpe − unigram` | 2000 | forms unseen in LM training | +0.1048 | [+0.0470, +0.1625] | **harm** (worse LM) (n=3) |
| `bpe − unigram` | 2000 | seen forms | +0.0183 | [-0.0203, +0.0569] | no detectable effect (n=3) |
| `bpe − unigram` | 4000 | all test text | +0.0532 | [-0.0333, +0.1396] | no detectable effect (n=3) |
| `bpe − unigram` | 4000 | held-out-lemma words | +0.0230 | [-0.0342, +0.0801] | no detectable effect (n=3) |
| `bpe − unigram` | 4000 | forms unseen in LM training | +0.1088 | [-0.0364, +0.2540] | no detectable effect (n=3) |
| `bpe − unigram` | 4000 | seen forms | +0.0429 | [-0.0385, +0.1244] | no detectable effect (n=3) |
