# Full-corpus scale-up (ur; PREREG.md §10)

Corpus: data/processed/ur_wiki20231101_pilot853889.txt — lines per split {'train': 683201, 'dev': 85383, 'test': 85305}. Gold types: dev 1618, test 1657. Fertility on 5,000 sampled dev lines.

| V | gold | unigram F1 | hard train-only F1 | ΔF1 per seed | mean ΔF1 [95% t-CI] | Δ tok/word | verdict |
|---|---|---|---|---|---|---|---|
| 4000 | dev silver (primary) | 0.1235 | 0.1393 | +0.0153, +0.0163, +0.0158 | +0.0158 [+0.0146, +0.0170] | +1.02% | **replicates** |
| 4000 | test silver (non-confirmatory) | 0.1350 | 0.1450 | +0.0097, +0.0108, +0.0095 | +0.0100 [+0.0083, +0.0117] | +1.02% | secondary (CI excludes 0) |
| 8000 | dev silver (primary) | 0.1695 | 0.1863 | +0.0156, +0.0185, +0.0159 | +0.0167 [+0.0127, +0.0207] | +2.20% | **replicates** |
| 8000 | test silver (non-confirmatory) | 0.1844 | 0.1969 | +0.0092, +0.0161, +0.0122 | +0.0125 [+0.0039, +0.0210] | +2.20% | secondary (CI excludes 0) |
| 16000 | dev silver (primary) | 0.1762 | 0.1965 | +0.0213, +0.0208, +0.0187 | +0.0203 [+0.0168, +0.0238] | +2.89% | **replicates** |
| 16000 | test silver (non-confirmatory) | 0.1682 | 0.1865 | +0.0177, +0.0163, +0.0209 | +0.0183 [+0.0125, +0.0241] | +2.89% | secondary (CI excludes 0) |
