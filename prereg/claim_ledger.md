# Claim ledger

Every claim the project might make, its current evidence, and its status.
Status values: **untested** · **pilot-only** · **supported** · **contradicted** ·
**unresolved** · **withdrawn**. Synthetic runs never change a status.

| Claim | Hypothesis | Evidence required | Evidence so far | Status |
|---|---|---|---|---|
| ZWNJ normalization explains most of the fertility difference | H1 | A1 on real corpora at matched vocab, ≥3 seeds; normalization share with CI | PILOT (Wikipedia 2023-11-01, 5k-line samples, V∈{2000,4000}, 3 seeds): every ZWNJ policy changes tokens/word by ≤0.001 (≤0.07%) in both languages, vs. BPE−Unigram gaps of 0.017–0.036 (sd). ZWNJ is too rare in this domain to explain fertility differences of any size. Normalization share vs a morphology-aware method not computable (no analyzer). Single domain. | pilot-only |
| ZWNJ is morphological in a minority of occurrences | H2 | A2: adjudicated stratified sample, Wilson CI, κ reported | PILOT: in real text ZWNJ is nearly absent (sd Wikipedia 2.9, ur Wikipedia 10.1 per 100k words; UD news ≈1 per 100k). In human normative annotation (Zia et al. 2018) it marks sub-word boundaries at 5.8 per 100 words, and those words appear joined *without* ZWNJ 119,813× vs 46× with it in ur Wikipedia. Reframing: ZWNJ marks sub-word boundaries *by norm* but is absent in practice; corpus occurrences are not yet labelled. docs/findings_pilot.md §1 | pilot-only |
| Analyzers provide reliable coverage | H3 | C1: coverage + precision vs manually reviewed dev gold | No rule/FST analyzer. Silver analyzer derived from manual UD/UniMorph lemmas covers 8.6%/27.4% (sd) and 15.1%/42.1% (ur) of pilot types/tokens; precision vs *independent* gold not measurable yet | untested |
| Soft prior beats plain/hard/normalized Unigram | H4 | B1 on test after freeze; B2 curve | PILOT (dev, silver, 3 seeds): soft λ=2 ≤ hard in both languages and both V; hard train-only beats plain Unigram on unseen lemmas (sd +0.019/+0.039 F1, ur +0.011/+0.014). Soft prior is the weaker variant | pilot-only (contradicted for soft at λ=2) |
| Gains survive vocab matching, seeds, data variation | H5 | B1 at all sizes, C2, F1 | PILOT: hard train-only gain holds at both V, both languages, 3 seeds; 20k-line scale check: docs/findings_pilot.md §7 | pilot-only |
| Gains are not length/memorisation/artefact | H6 | C3 negative control, D1 strata | PILOT: random-boundary control with matched coverage, count *and* tokens/word recovers ≤~20% (sd) / none (ur) of the F1 gain | pilot-only |
| Intrinsic gains need not transfer downstream | H7 | G1 | PROXY only: token-bigram bits/char is 0.2–0.6% *worse* for the supervised tokenizer in both languages (docs/findings_pilot.md §5c); no neural LM yet | untested (proxy consistent) |
| Method is transparent and cheap | H8 | complexity analysis + timings | reference implementation exists; O(n·L) per word documented | pilot-only |
| Objective A is a new method | — | completed novelty screen (docs/novelty_screening.md) | Screen done: A = posterior regularization with a fixed dual (Ganchev et al. 2010); B = pre-segmentation | withdrawn |

## Change log

| Date | Claim | Old → new status | Evidence (run IDs) |
|---|---|---|---|
| 2026-10-29 | H1 | untested → pilot-only | runs/SD-G0-*, runs/UR-G0-* (exploratory; prereg not frozen) |
| 2026-10-29 | H2 | untested → pilot-only | SD/UR-*G1*, data/gold/ur_zia_zwnj.stats.json |
| 2026-10-29 | H4, H5, H6 | untested → pilot-only | SD/UR-EVAL-*, *-randctrl-* |
| 2026-10-29 | Objective A novelty | untested → withdrawn | docs/novelty_screening.md |
