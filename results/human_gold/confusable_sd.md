# Confusable test re-scored with native-approved substitutions (sd)

Substitution: {'ي': 'ی'}. Reviewer rejected (DIFFERENT/UNSURE) original forms: کي.
Perturbed test tokens: 4511; approved: 4280 (231 removed).

Drop = clean accuracy − perturbed accuracy on the same tokens (mean over seeds). Lower is more robust.

| system | budget | confusable drop (all) | confusable drop (approved) | noise drop (approved) | Δ approved conf. drop vs word [95% t-CI] |
|---|---|---|---|---|---|
| char | 0.01 | 0.063 | 0.065 | 0.125 | -0.162 [-0.220, -0.104] (n=5) |
| concat_unigram | 0.01 | 0.225 | 0.208 | 0.237 | -0.020 [-0.155, +0.114] (n=5) |
| gated_bpe | 0.01 | 0.145 | 0.118 | 0.162 | -0.110 [-0.175, -0.044] (n=5) |
| gated_unigram | 0.01 | 0.145 | 0.145 | 0.204 | -0.083 [-0.227, +0.061] (n=5) |
| gated_unigram_hard_trainonly | 0.01 | 0.141 | 0.116 | 0.181 | -0.112 [-0.151, -0.072] (n=5) |
| sub_bpe | 0.01 | 0.243 | 0.207 | 0.209 | -0.021 [-0.131, +0.089] (n=5) |
| sub_unigram | 0.01 | 0.218 | 0.182 | 0.186 | -0.046 [-0.142, +0.051] (n=5) |
| sub_unigram_hard_trainonly | 0.01 | 0.196 | 0.179 | 0.166 | -0.048 [-0.135, +0.039] (n=5) |
| word | 0.01 | 0.267 | 0.228 | 0.226 |  |
| char | 0.1 | 0.184 | 0.163 | 0.288 | -0.331 [-0.471, -0.190] (n=5) |
| concat_unigram | 0.1 | 0.322 | 0.291 | 0.375 | -0.203 [-0.366, -0.040] (n=5) |
| gated_bpe | 0.1 | 0.231 | 0.215 | 0.339 | -0.279 [-0.406, -0.152] (n=5) |
| gated_unigram | 0.1 | 0.269 | 0.243 | 0.352 | -0.251 [-0.421, -0.081] (n=5) |
| gated_unigram_hard_trainonly | 0.1 | 0.219 | 0.196 | 0.342 | -0.298 [-0.479, -0.117] (n=5) |
| sub_bpe | 0.1 | 0.409 | 0.377 | 0.389 | -0.117 [-0.183, -0.051] (n=5) |
| sub_unigram | 0.1 | 0.422 | 0.399 | 0.404 | -0.095 [-0.179, -0.012] (n=5) |
| sub_unigram_hard_trainonly | 0.1 | 0.358 | 0.325 | 0.373 | -0.169 [-0.234, -0.105] (n=5) |
| word | 0.1 | 0.519 | 0.494 | 0.490 |  |
| char | 1 | 0.283 | 0.262 | 0.340 | -0.213 [-0.699, +0.273] (n=3) |
| concat_unigram | 1 | 0.361 | 0.326 | 0.406 | -0.149 [-0.504, +0.207] (n=3) |
| gated_bpe | 1 | 0.349 | 0.315 | 0.404 | -0.160 [-0.583, +0.264] (n=3) |
| gated_unigram | 1 | 0.365 | 0.338 | 0.408 | -0.137 [-0.419, +0.145] (n=3) |
| gated_unigram_hard_trainonly | 1 | 0.326 | 0.292 | 0.392 | -0.183 [-0.595, +0.228] (n=3) |
| sub_bpe | 1 | 0.451 | 0.426 | 0.429 | -0.049 [-0.118, +0.021] (n=3) |
| sub_unigram | 1 | 0.415 | 0.397 | 0.423 | -0.078 [-0.228, +0.072] (n=3) |
| sub_unigram_hard_trainonly | 1 | 0.376 | 0.343 | 0.415 | -0.132 [-0.220, -0.044] (n=3) |
| word | 1 | 0.501 | 0.475 | 0.473 |  |
