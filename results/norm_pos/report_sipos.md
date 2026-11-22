# Normalization x POS tagging: SiPOS (primary)

18 runs; seeds [0, 1, 2]. Accuracy on the test split (mean over seeds). `keyboard` = the test typed as on an Urdu keyboard; `noise` = one random letter changed in the same tokens; `pert` = only the altered tokens.

| tagger | normalizer | clean | keyboard | noise | clean (pert) | keyboard (pert) | restored |
|---|---|---|---|---|---|---|---|
| word | none | 0.9821 | 0.4942 | 0.5006 | 0.9802 | 0.1880 | 0.0000 |
| word | 0.1.0 rules | 0.9813 | 0.9252 | 0.4811 | 0.9795 | 0.8885 | 0.8886 |
| word | 0.2.0 keyboard | 0.9806 | 0.9239 | 0.5004 | 0.9787 | 0.8864 | 0.8830 |
| char | none | 0.9777 | 0.6312 | 0.6170 | 0.9748 | 0.4137 | 0.0000 |
| char | 0.1.0 rules | 0.9756 | 0.9312 | 0.6267 | 0.9724 | 0.9004 | 0.8886 |
| char | 0.2.0 keyboard | 0.9763 | 0.9306 | 0.6230 | 0.9727 | 0.8985 | 0.8830 |

## Paired contrasts (mean difference, 95% t-interval over seeds)

| tagger | contrast | test | Δ accuracy | 95% CI | verdict |
|---|---|---|---|---|---|
| word | 0.2.0 keyboard − none | keyboard-typed | +0.4297 | [+0.3816, +0.4778] | **helps** (H9a) |
| word | 0.2.0 keyboard − none | clean | -0.0016 | [-0.0130, +0.0098] | **no harm** (H9b) |
| word | 0.2.0 keyboard − none | noise control | -0.0003 | [-0.1121, +0.1116] |  |
| word | 0.1.0 rules − none | keyboard-typed | +0.4311 | [+0.3742, +0.4879] | interval excludes 0 |
| word | 0.1.0 rules − none | clean | -0.0009 | [-0.0034, +0.0017] |  |
| word | 0.1.0 rules − none | noise control | -0.0196 | [-0.1301, +0.0910] |  |
| word | 0.2.0 keyboard − 0.1.0 rules | keyboard-typed | -0.0014 | [-0.0101, +0.0074] |  |
| word | 0.2.0 keyboard − 0.1.0 rules | clean | -0.0007 | [-0.0096, +0.0082] |  |
| word | 0.2.0 keyboard − 0.1.0 rules | noise control | +0.0193 | [-0.2024, +0.2410] |  |
| char | 0.2.0 keyboard − none | keyboard-typed | +0.2994 | [+0.1615, +0.4372] | interval excludes 0 |
| char | 0.2.0 keyboard − none | clean | -0.0014 | [-0.0068, +0.0040] |  |
| char | 0.2.0 keyboard − none | noise control | +0.0060 | [-0.0066, +0.0187] |  |
| char | 0.1.0 rules − none | keyboard-typed | +0.2999 | [+0.1001, +0.4998] | interval excludes 0 |
| char | 0.1.0 rules − none | clean | -0.0021 | [-0.0065, +0.0023] |  |
| char | 0.1.0 rules − none | noise control | +0.0097 | [-0.0180, +0.0373] |  |
| char | 0.2.0 keyboard − 0.1.0 rules | keyboard-typed | -0.0006 | [-0.0672, +0.0660] |  |
| char | 0.2.0 keyboard − 0.1.0 rules | clean | +0.0007 | [-0.0034, +0.0048] |  |
| char | 0.2.0 keyboard − 0.1.0 rules | noise control | -0.0036 | [-0.0280, +0.0207] |  |

## Recovery fraction

(acc_keyboard(N) − acc_keyboard(none)) / (acc_clean(none) − acc_keyboard(none)), mean over seeds.

| tagger | 0.1.0 rules | 0.2.0 keyboard |
|---|---|---|
| word | 0.883 | 0.881 |
| char | 0.858 | 0.866 |

## Preregistered verdicts (SiPOS, word tagger)

* H9a: **helps** (H9a)
* H9b: **no harm** (H9b)
