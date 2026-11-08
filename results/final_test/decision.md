# Final test evaluation under prereg-v1

Evaluated once on the frozen commit with `04_intrinsic_eval.py --split test --final`. Test gold is **silver** (lemma-derived; on Sindhi dev it had P = 0.55 vs native gold). 3 seeds, already-trained pilot models.

## Primary contrast: `unigram_hard_trainonly − unigram`

| lang | V | mean ΔF1 | 95% t-CI | 98.75% t-CI (Bonferroni) | Δ tok/word (rel.) | verdict |
|---|---|---|---|---|---|---|
| sd | 2000 | +0.0301 | [+0.0203, +0.0398] | [+0.0099, +0.0502] | +1.73% | **PASS** (survives Bonferroni) |
| sd | 4000 | +0.0331 | [+0.0167, +0.0496] | [-0.0007, +0.0670] | +3.01% | **PASS** |
| ur | 2000 | +0.0064 | [+0.0043, +0.0084] | [+0.0021, +0.0106] | +1.16% | **FAIL** |
| ur | 4000 | +0.0115 | [+0.0079, +0.0150] | [+0.0042, +0.0188] | +1.40% | **PASS** (survives Bonferroni) |

## Secondary contrasts (reported, not decisive)

| lang | V | contrast | mean ΔF1 [95% t-CI] |
|---|---|---|---|
| sd | 2000 | `unigram_soft_trainonly − unigram` | +0.0033 [-0.0128, +0.0194] |
| sd | 2000 | `unigram_soft − unigram_hard` | -0.0268 [-0.0371, -0.0164] |
| sd | 2000 | `bpe − unigram` | -0.0138 [-0.0242, -0.0034] |
| sd | 2000 | `unigram_zwnj_norm − unigram` | +0.0007 [-0.0008, +0.0022] |
| sd | 4000 | `unigram_soft_trainonly − unigram` | +0.0049 [-0.0021, +0.0119] |
| sd | 4000 | `unigram_soft − unigram_hard` | -0.0282 [-0.0383, -0.0182] |
| sd | 4000 | `bpe − unigram` | -0.0372 [-0.0505, -0.0239] |
| sd | 4000 | `unigram_zwnj_norm − unigram` | +0.0005 [-0.0016, +0.0026] |
| ur | 2000 | `unigram_soft_trainonly − unigram` | +0.0007 [-0.0034, +0.0048] |
| ur | 2000 | `unigram_soft − unigram_hard` | -0.0056 [-0.0112, -0.0001] |
| ur | 2000 | `bpe − unigram` | -0.0215 [-0.0374, -0.0057] |
| ur | 2000 | `unigram_zwnj_norm − unigram` | +0.0002 [-0.0009, +0.0012] |
| ur | 4000 | `unigram_soft_trainonly − unigram` | +0.0025 [+0.0004, +0.0047] |
| ur | 4000 | `unigram_soft − unigram_hard` | -0.0089 [-0.0142, -0.0036] |
| ur | 4000 | `bpe − unigram` | -0.0326 [-0.0489, -0.0162] |
| ur | 4000 | `unigram_zwnj_norm − unigram` | -0.0003 [-0.0021, +0.0016] |
