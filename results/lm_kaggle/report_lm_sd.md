# Gate 5 language-model results (sd)

18 runs. Bits per character (lower is better), mean ± sd over seeds.

| tokenizer | V | test bpc | held-out-lemma bpc | unseen-form bpc | tokens/char | steps |
|---|---|---|---|---|---|---|
| bpe | 2000 | 2.3948 ± 0.0035 | 1.8258 ± 0.0077 | 4.3423 ± 0.0515 | 0.561 | 2417 |
| unigram | 2000 | 2.3902 ± 0.0314 | 1.8216 ± 0.0219 | 4.2532 ± 0.0034 | 0.568 | 2500 |
| unigram_hard_trainonly | 2000 | 2.3928 ± 0.0297 | 1.8136 ± 0.0244 | 4.2351 ± 0.0579 | 0.574 | 2417 |
| bpe | 4000 | 2.4105 ± 0.0255 | 1.8199 ± 0.0156 | 4.3415 ± 0.0202 | 0.517 | 2250 |
| unigram | 4000 | 2.3881 ± 0.0297 | 1.8083 ± 0.0139 | 4.2529 ± 0.0031 | 0.520 | 2250 |
| unigram_hard_trainonly | 4000 | 2.3867 ± 0.0269 | 1.7983 ± 0.0182 | 4.2644 ± 0.0744 | 0.529 | 2333 |

## Paired contrasts (Δbpc = system − reference; 95% t-interval over seeds)

| contrast | V | text | Δbpc | 95% CI | verdict (§9 rule) |
|---|---|---|---|---|---|
| `unigram_hard_trainonly − unigram` (primary) | 2000 | all test text | +0.0026 | [-0.0137, +0.0190] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 2000 | held-out-lemma words | -0.0080 | [-0.0555, +0.0395] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 2000 | forms unseen in LM training | -0.0181 | [-0.1586, +0.1223] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 2000 | seen forms | +0.0063 | [-0.0374, +0.0499] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` (primary) | 4000 | all test text | -0.0014 | [-0.1282, +0.1253] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 4000 | held-out-lemma words | -0.0100 | [-0.0894, +0.0694] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 4000 | forms unseen in LM training | +0.0116 | [-0.1774, +0.2006] | no detectable effect (n=3) |
| `unigram_hard_trainonly − unigram` | 4000 | seen forms | -0.0037 | [-0.1425, +0.1351] | no detectable effect (n=3) |
| `bpe − unigram` | 2000 | all test text | +0.0045 | [-0.0693, +0.0784] | no detectable effect (n=3) |
| `bpe − unigram` | 2000 | held-out-lemma words | +0.0042 | [-0.0670, +0.0754] | no detectable effect (n=3) |
| `bpe − unigram` | 2000 | forms unseen in LM training | +0.0891 | [-0.0335, +0.2117] | no detectable effect (n=3) |
| `bpe − unigram` | 2000 | seen forms | -0.0102 | [-0.1085, +0.0881] | no detectable effect (n=3) |
| `bpe − unigram` | 4000 | all test text | +0.0224 | [-0.0787, +0.1235] | no detectable effect (n=3) |
| `bpe − unigram` | 4000 | held-out-lemma words | +0.0116 | [-0.0506, +0.0738] | no detectable effect (n=3) |
| `bpe − unigram` | 4000 | forms unseen in LM training | +0.0887 | [+0.0328, +0.1445] | **harm** (worse LM) (n=3) |
| `bpe − unigram` | 4000 | seen forms | +0.0108 | [-0.0999, +0.1216] | no detectable effect (n=3) |
