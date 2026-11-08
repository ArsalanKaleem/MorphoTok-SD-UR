# Claim ledger

Every claim the project might make, its current evidence, and its status.
Status values: **untested** · **pilot-only** · **supported** · **contradicted** ·
**unresolved** · **withdrawn**. Synthetic runs never change a status.

| Claim | Hypothesis | Evidence required | Evidence so far | Status |
|---|---|---|---|---|
| ZWNJ normalization explains most of the fertility difference | H1 | A1 on real corpora at matched vocab, ≥3 seeds; normalization share with CI | PILOT (Wikipedia 2023-11-01, 5k-line samples, V∈{2000,4000}, 3 seeds): every ZWNJ policy changes tokens/word by ≤0.001 (≤0.07%) in both languages, vs. BPE−Unigram gaps of 0.017–0.036 (sd). ZWNJ is too rare in this domain to explain fertility differences of any size. Normalization share vs a morphology-aware method not computable (no analyzer). Single domain. | pilot-only |
| ZWNJ is morphological in a minority of occurrences | H2 | A2: adjudicated stratified sample, Wilson CI, κ reported | PILOT: in real text ZWNJ is nearly absent (sd Wikipedia 2.9, ur Wikipedia 10.1 per 100k words; UD news ≈1 per 100k). In human normative annotation (Zia et al. 2018) it marks sub-word boundaries at 5.8 per 100 words, and those words appear joined *without* ZWNJ 119,813× vs 46× with it in ur Wikipedia. Reframing: ZWNJ marks sub-word boundaries *by norm* but is absent in practice; corpus occurrences are not yet labelled. docs/findings_pilot.md §1 **HUMAN (sd, 1 native annotator, 109 Wikipedia occurrences):** 85–92 are FOREIGN or ERROR; of the rest MORPH = 12/24 (pass 1) / 13/17 = 0.76, Wilson (0.53, 0.90) (pass 2, after AI critique). 9/13 are Arabic ال-names; ≈7 distinct types. docs/findings_human_review.md §3 | **contradicted (sd)** for occurrences in Sindhi text; ur not tested (no review planned) |
| Analyzers provide reliable coverage | H3 | C1: coverage + precision vs manually reviewed dev gold | No rule/FST analyzer. Silver analyzer derived from manual UD/UniMorph lemmas covers 8.6%/27.4% (sd) and 15.1%/42.1% (ur) of pilot types/tokens; precision vs *independent* gold not measurable yet **HUMAN (sd, 267 dev words):** silver P = 0.553, R = 0.477, F1 = 0.512 vs native gold. docs/findings_human_review.md §1 | **contradicted (sd)**: silver precision ≈ 0.55 |
| Soft prior beats plain/hard/normalized Unigram | H4 | B1 on test after freeze; B2 curve | PILOT (dev, silver, 3 seeds): soft λ=2 ≤ hard in both languages and both V; hard train-only beats plain Unigram on unseen lemmas (sd +0.019/+0.039 F1, ur +0.011/+0.014). Soft prior is the weaker variant **HUMAN (sd, 267 words):** soft train-only vs unigram +0.002 [−0.009, +0.013] (V4000), −0.001 (V2000); hard train-only +0.022 [+0.002, +0.043] (V4000), +0.001 [−0.006, +0.008] (V2000) **CONFIRMATORY TEST (prereg-v1, silver test gold):** hard train-only − unigram: sd +0.030 [+0.020, +0.040] (V2000), +0.033 [+0.017, +0.050] (V4000); ur +0.006 [+0.004, +0.008] (V2000, below +0.010), +0.012 [+0.008, +0.015] (V4000). Soft − hard < 0 in all four cells. results/final_test/decision.md | **supported (hard train-only, 3/4 preregistered tests, silver test gold)**; soft prior contradicted |
| Gains survive vocab matching, seeds, data variation | H5 | B1 at all sizes, C2, F1 | PILOT: hard train-only gain holds at both V, both languages, 3 seeds; 20k-line scale check: docs/findings_pilot.md §7 **HUMAN (sd):** hard train-only gain does not survive at V=2000 against native gold **TEST:** passes at both V in sd and at V4000 in ur; ur V2000 gain significant but below threshold | partly supported (fails ur V2000 threshold; sd V2000 not supported on human dev gold) |
| Gains are not length/memorisation/artefact | H6 | C3 negative control, D1 strata | PILOT: random-boundary control with matched coverage, count *and* tokens/word recovers ≤~20% (sd) / none (ur) of the F1 gain | pilot-only |
| Intrinsic gains need not transfer downstream | H7 | G1 | PROXY only: token-bigram bits/char is 0.2–0.6% *worse* for the supervised tokenizer in both languages (docs/findings_pilot.md §5c); no neural LM yet | untested (proxy consistent) |
| Method is transparent and cheap | H8 | complexity analysis + timings | reference implementation exists; O(n·L) per word documented | pilot-only |
| Character fusion improves unseen-lemma POS accuracy (C1) | C1 | P1 grid, paired vs word, ≥3 seeds, 2 languages | PILOT. CPU BiLSTM: `gated:*` beats `word` on unseen lemmas at full budget (sd +0.050 to +0.076, CIs exclude 0; ur CIs include 0). **XLM-R (T4, 3 seeds): no gain at 10%/100%; loss at 1% (sd gated−base −0.041 [−0.050, −0.031]; concat sd −0.034, ur −0.019).** | **contradicted for a pretrained encoder**; pilot-only for from-scratch taggers |
| Character input gives spelling robustness beyond random-noise robustness (C2) | C2 | confusable vs noise drops, native-approved variants | PILOT: char input cuts confusable-substitution drops by 0.2–0.4 (CPU) and by +0.02 to +0.11 with XLM-R (e.g. sd concat−base +0.050 [+0.010, +0.091] at 100%; ur gated−base +0.029 [+0.013, +0.045] at 1%), both languages; substitution not yet native-approved; edit count differs from the control **HUMAN (sd):** ي→ی approved SAME in 30/31 pairs; re-scored on approved substitutions only (کي tokens removed), char/gated drops still 0.28–0.33 below word at 10% budget, CIs exclude 0; XLM-R not re-scored (no per-token bits) | pilot-only (**substitution native-approved, sd**; ur not reviewed) |
| Fusion gain is largest at low budgets (C3) | C3 | budget curves | PILOT: overall-accuracy gains vs word are largest at 1% (sd +0.14 to +0.18; ur up to +0.26) and shrink to ≈+0.01 at 100% | pilot-only |
| Gated > parameter-matched concat (C4) | C4 | gated vs concat, paired | PILOT: CPU only at the 10% budget (unseen lemma ≈ +0.03); XLM-R: no robustness difference, unseen-lemma +0.011 to +0.013 in two cells only | weak; gate not the contribution |
| Tokenizer morphology and character input are complementary (C5) | C5 | gated:hard vs gated:unigram | PILOT: vs the same tokenizer without supervision (`gated:unigram`), sd +0.011 to +0.026 unseen-lemma at all budgets (CIs exclude 0); ur same direction, not significant. vs `gated:bpe` (sd): ahead but CIs include 0 | pilot-only (sd only; not shown vs BPE) |
| Objective A is a new method | — | completed novelty screen (docs/novelty_screening.md) | Screen done: A = posterior regularization with a fixed dual (Ganchev et al. 2010); B = pre-segmentation | withdrawn |

## Change log

| Date | Claim | Old → new status | Evidence (run IDs) |
|---|---|---|---|
| 2026-10-29 | H1 | untested → pilot-only | runs/SD-G0-*, runs/UR-G0-* (exploratory; prereg not frozen) |
| 2026-10-29 | H2 | untested → pilot-only | SD/UR-*G1*, data/gold/ur_zia_zwnj.stats.json |
| 2026-10-29 | H4, H5, H6 | untested → pilot-only | SD/UR-EVAL-*, *-randctrl-* |
| 2026-10-29 | Objective A novelty | untested → withdrawn | docs/novelty_screening.md |
| 2026-11-05 | C1–C5 | (new) → pilot-only | SD-POS-*, UR-POS-*, docs/findings_pos.md |
| 2026-11-08 | C1 | pilot-only → contradicted for XLM-R | results/xlmr_kaggle/results_{sd,ur}.jsonl |
| 2026-11-08 | C2, C4 | evidence added (XLM-R) | results/xlmr_kaggle/report_{sd,ur}.md |
| 2026-11-09 | H2 | pilot-only → contradicted (sd) | data/audit/review/sd_zwnj.tsv (AK), docs/findings_human_review.md |
| 2026-11-09 | H3 | untested → contradicted (sd) | results/human_gold/report_sd.md |
| 2026-11-09 | H4, H5 | evidence added (human gold, sd) | results/human_gold/report_sd.md |
| 2026-11-09 | C2 | evidence added (approved substitutions, sd) | results/human_gold/confusable_sd.md |
| 2026-11-09 | all | AI-assisted collaborator labels (2026-11-08) excluded as evidence | data/audit/review/ai_assisted_2026-11-08/PROVENANCE.md |
| 2026-11-09 | all (ur), H2/H3 κ | scope: no Urdu review and no second annotator planned; Urdu claims stay silver-only | HONESTY.md, prereg/decision_gates.md |
| 2026-11-09 | H4–H6 | primary contrast and thresholds fixed before the test evaluation | prereg/PREREG.md §4 |
| 2026-11-09 | H4, H5 | → supported / partly supported (confirmatory, silver test gold) | prereg-v1; results/final_test/decision.md |
