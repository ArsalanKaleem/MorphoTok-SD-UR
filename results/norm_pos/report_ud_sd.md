# Normalization x POS tagging: UD Sindhi-Isra (replication, secondary)

18 runs; seeds [0, 1, 2]. Accuracy on the test split (mean over seeds). `keyboard` = the test typed as on an Urdu keyboard; `noise` = one random letter changed in the same tokens; `pert` = only the altered tokens.

| tagger | normalizer | clean | keyboard | noise | clean (pert) | keyboard (pert) | restored |
|---|---|---|---|---|---|---|---|
| word | none | 0.9080 | 0.6221 | 0.5905 | 0.9004 | 0.3938 | 0.0000 |
| word | 0.1.0 rules | 0.9098 | 0.8805 | 0.5619 | 0.9015 | 0.8500 | 0.8736 |
| word | 0.2.0 keyboard | 0.9116 | 0.8822 | 0.5651 | 0.9036 | 0.8514 | 0.8707 |
| char | none | 0.9127 | 0.7142 | 0.6798 | 0.9048 | 0.5558 | 0.0000 |
| char | 0.1.0 rules | 0.9130 | 0.8920 | 0.6830 | 0.9061 | 0.8687 | 0.8736 |
| char | 0.2.0 keyboard | 0.9162 | 0.8863 | 0.6752 | 0.9101 | 0.8572 | 0.8707 |

## Paired contrasts (mean difference, 95% t-interval over seeds)

| tagger | contrast | test | Δ accuracy | 95% CI | verdict |
|---|---|---|---|---|---|
| word | 0.2.0 keyboard − none | keyboard-typed | +0.2602 | [+0.2238, +0.2965] | interval excludes 0 |
| word | 0.2.0 keyboard − none | clean | +0.0036 | [-0.0088, +0.0159] |  |
| word | 0.2.0 keyboard − none | noise control | -0.0254 | [-0.1267, +0.0760] |  |
| word | 0.1.0 rules − none | keyboard-typed | +0.2584 | [+0.2182, +0.2986] | interval excludes 0 |
| word | 0.1.0 rules − none | clean | +0.0018 | [-0.0180, +0.0216] |  |
| word | 0.1.0 rules − none | noise control | -0.0286 | [-0.0849, +0.0277] |  |
| word | 0.2.0 keyboard − 0.1.0 rules | keyboard-typed | +0.0017 | [-0.0176, +0.0211] |  |
| word | 0.2.0 keyboard − 0.1.0 rules | clean | +0.0017 | [-0.0169, +0.0204] |  |
| word | 0.2.0 keyboard − 0.1.0 rules | noise control | +0.0033 | [-0.0474, +0.0539] |  |
| char | 0.2.0 keyboard − none | keyboard-typed | +0.1721 | [-0.0227, +0.3670] |  |
| char | 0.2.0 keyboard − none | clean | +0.0035 | [+0.0005, +0.0065] | interval excludes 0 |
| char | 0.2.0 keyboard − none | noise control | -0.0046 | [-0.0678, +0.0586] |  |
| char | 0.1.0 rules − none | keyboard-typed | +0.1778 | [-0.0338, +0.3894] |  |
| char | 0.1.0 rules − none | clean | +0.0003 | [-0.0118, +0.0123] |  |
| char | 0.1.0 rules − none | noise control | +0.0032 | [-0.0367, +0.0431] |  |
| char | 0.2.0 keyboard − 0.1.0 rules | keyboard-typed | -0.0057 | [-0.0226, +0.0112] |  |
| char | 0.2.0 keyboard − 0.1.0 rules | clean | +0.0033 | [-0.0114, +0.0179] |  |
| char | 0.2.0 keyboard − 0.1.0 rules | noise control | -0.0078 | [-0.0389, +0.0233] |  |

## Recovery fraction

(acc_keyboard(N) − acc_keyboard(none)) / (acc_clean(none) − acc_keyboard(none)), mean over seeds.

| tagger | 0.1.0 rules | 0.2.0 keyboard |
|---|---|---|
| word | 0.903 | 0.909 |
| char | 0.867 | 0.847 |
