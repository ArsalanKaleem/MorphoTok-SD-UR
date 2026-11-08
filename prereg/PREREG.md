# Preregistration — MorphoTok-SD-UR

**Status:** thresholds filled on 2026-11-09 after the dev-split pilot. Whether this
document is frozen is determined only by `python scripts/prereg_freeze.py status` (a
`prereg-v*` git tag whose prereg files equal the working tree). Do not state that it is
frozen anywhere else.

**What was known when the thresholds were set.** All dev-split results in
`docs/findings_pilot.md`, `docs/findings_pos.md` and `docs/findings_human_review.md` had been
seen. The tokenizer **test** split had never been evaluated (`runs/ledger.jsonl` contains no
test record). The POS study used the UD test split during the pilot, so **POS results are
exploratory and are not covered by this preregistration.** Only the intrinsic tokenizer
contrasts below are confirmatory.

Freeze procedure: complete the pilot, fill in every `UNRESOLVED` field that the pilot
justifies, commit, then run `make prereg-freeze`. After freezing, changes go in
`prereg/AMENDMENTS.md` with a new tag (`prereg-v2`, …).

## 1. Research questions

Whether morphology-aware and/or ZWNJ-aware segmentation improves Sindhi and Urdu
tokenization beyond normalization alone, under matched vocabulary, multiple seeds,
domain variation and analyzer errors (H1–H8, `claim_ledger.md`).

## 2. Hypotheses (all unverified)

| ID | Statement | Registry experiments | Gate |
|---|---|---|---|
| H1 | ZWNJ normalization alone explains most observed fertility differences | A1 | 0 |
| H2 | ZWNJ marks genuine morphological boundaries in only a minority of occurrences | A2 | 1 |
| H3 | Available analyzers give enough reliable coverage for useful boundary supervision | C1 | 2 |
| H4 | A confidence-weighted soft boundary prior beats plain, hard and ZWNJ-normalized Unigram at matched vocabulary | B1, B2, C2 | 3 |
| H5 | Any gain survives vocabulary matching, seeds and data variation | B1, C2, F1 | 3 |
| H6 | Alignment gains are not explained by longer tokens, memorisation or evaluation artefacts | C3, D1 | 3 |
| H7 | Better morphological segmentation does not necessarily imply better downstream LM | G1 | 5 |
| H8 | The method is transparent and computationally reasonable | B2, E1 | 3 |

## 3. Data

| Item | Sindhi | Urdu |
|---|---|---|
| Corpus, licence, domain | Wikipedia 2023-11-01 (`wikimedia/wikipedia`), CC BY-SA 3.0 / GFDL, encyclopedia | same |
| Size (lines / words) | 5,000-line pilot sample (`data/processed/sd_wiki20231101_pilot5000.txt`; hashes in its manifest) | 5,000-line pilot sample (`ur_wiki20231101_pilot5000.txt`) |
| Gold boundary set (size, annotators, dev/test sizes) | **test: SILVER**, lemma-derived from UD Sindhi-Isra, 914 test types (339 with a boundary), split by lemma. Dev also has 267 human-reviewed words (1 native annotator), dev only | **test: SILVER**, UD Urdu-UDTB + UniMorph, 1,657 test types; no human review |
| ZWNJ annotation sample | 109 Wikipedia occurrences, 1 native annotator (descriptive; not a confirmatory test) | none (normative reference: Zia et al. 2018) |
| Analyzer (name, version, licence) | none; supervision = silver boundaries of TRAIN-split lemmas (`lemma_derived`, CC BY-SA 4.0 via UD) | same (UD + UniMorph) |

Splits: content-hashed line splits 80/10/10 (salt fixed in `configs/data/*.yaml`); gold
types split dev/test by type. Test annotations are never used for tuning.

## 4. Primary outcome

* **Primary metric:** micro boundary F1 over gold word types in stripped coordinates
  (`src/morphtok/eval/morph_boundary.py`), on the **test** gold split, at each
  preregistered vocabulary size.
* **Primary contrast:** `unigram_hard_trainonly − unigram` (supervision only during
  training; test lemmas are never supervised), in each language at V = 2000 and V = 4000:
  four primary tests. Changed from the draft's soft-prior contrast because the dev pilot
  showed hard ≥ soft (`docs/findings_pilot.md` §3; Gate 3 "revise").
* **Success threshold (minimum F1 gain):** mean ΔF1 over seeds ≥ **+0.010** **and** the
  95% t-interval over the 3 per-seed deltas excludes 0.
* **Maximum acceptable fertility increase:** Δ tokens/word ≤ **+5%** of `unigram`'s value.
* **Secondary contrasts (reported, not decisive):** `unigram_soft_trainonly − unigram`,
  `unigram_soft − unigram_hard`, `bpe − unigram`, `unigram_zwnj_norm − unigram`.
* **Caveat fixed in advance:** the test gold is silver; on the Sindhi dev split silver
  boundaries had P = 0.55, R = 0.48 against native review. A pass on silver test is
  evidence about agreement with lemma-derived boundaries, not with native gold.

## 5. Secondary outcomes

Exact-match accuracy; fertility (tokens per raw orthographic word); tokens per stripped
character; mean token length; frequency-stratified and coverage-stratified F1;
normalization share; sampling entropy; (Gate 5) downstream metrics.

## 6. Analysis plan

* Vocabulary sizes: **2000 and 4000** (both above the ≈400-character inventory); every
  system at the same sizes; realised sizes recorded and mismatches reported.
* Seeds: **3** (0, 1, 2): the already-trained pilot models; seeds vary the training
  subsample and resampling. No model is retrained for the test evaluation.
* Uncertainty: paired bootstrap (1000 resamples) over gold types for F1 and over lines
  for fertility; approximate randomization test; t-interval over per-seed deltas;
  Cohen's d_z over seeds.
* Multiple comparisons: all four primary tests reported with uncorrected 95% intervals;
  each is also marked as surviving **Bonferroni** if its 98.75% (= 1 − 0.05/4) t-interval
  over seeds excludes 0.
* The test evaluation is run **once**, with `scripts/04_intrinsic_eval.py --split test --final`
  on the frozen commit, and reported whatever the outcome.
* Hyperparameters (λ, penalty mapping, min_confidence) selected on **dev only**.
* Every run, including failed ones, is in `runs/ledger.jsonl`.

## 7. Exploratory vs confirmatory

Everything run before the freeze tag is **pilot/exploratory**. Synthetic-data runs are
integration tests and are never evidence for any hypothesis.

## 8. Deviations

Recorded in `prereg/AMENDMENTS.md`.
