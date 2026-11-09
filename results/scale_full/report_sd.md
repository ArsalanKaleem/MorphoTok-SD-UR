# Full-corpus scale-up (sd; PREREG.md §10)

Corpus: data/processed/sd_wiki20231101_pilot66141.txt — lines per split {'train': 53036, 'dev': 6532, 'test': 6573}. Gold types: dev 961, test 914, native dev words 267. Fertility on 5,000 sampled dev lines.

| V | gold | unigram F1 | hard train-only F1 | ΔF1 per seed | mean ΔF1 [95% t-CI] | Δ tok/word | verdict |
|---|---|---|---|---|---|---|---|
| 4000 | dev silver (primary) | 0.1852 | 0.2150 | +0.0310, +0.0335, +0.0249 | +0.0298 [+0.0187, +0.0409] | +2.90% | **replicates** |
| 4000 | test silver (non-confirmatory) | 0.1984 | 0.2330 | +0.0300, +0.0350, +0.0386 | +0.0345 [+0.0239, +0.0452] | +2.90% | secondary (CI excludes 0) |
| 4000 | native dev | 0.2964 | 0.3220 | +0.0181, +0.0295, +0.0291 | +0.0256 [+0.0095, +0.0417] | +2.90% | secondary (CI excludes 0) |
| 8000 | dev silver (primary) | 0.1965 | 0.2310 | +0.0333, +0.0369, +0.0332 | +0.0345 [+0.0292, +0.0397] | +3.93% | **replicates** |
| 8000 | test silver (non-confirmatory) | 0.2092 | 0.2435 | +0.0338, +0.0379, +0.0314 | +0.0343 [+0.0262, +0.0425] | +3.93% | secondary (CI excludes 0) |
| 8000 | native dev | 0.3019 | 0.3314 | +0.0256, +0.0355, +0.0273 | +0.0295 [+0.0163, +0.0427] | +3.93% | secondary (CI excludes 0) |
| 16000 | dev silver (primary) | 0.1809 | 0.2318 | +0.0605, +0.0482, +0.0438 | +0.0508 [+0.0293, +0.0724] | +4.82% | **replicates** |
| 16000 | test silver (non-confirmatory) | 0.2068 | 0.2555 | +0.0424, +0.0540, +0.0494 | +0.0486 [+0.0341, +0.0632] | +4.82% | secondary (CI excludes 0) |
| 16000 | native dev | 0.2116 | 0.2415 | +0.0426, +0.0257, +0.0215 | +0.0299 [+0.0021, +0.0578] | +4.82% | secondary (CI excludes 0) |
