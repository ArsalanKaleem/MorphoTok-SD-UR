# Preregistration — MorphoTok-SD-UR

**Status: DRAFT, NOT FROZEN.** Whether this document is frozen is determined only by
`python scripts/prereg_freeze.py status` (a `prereg-v*` git tag whose prereg files equal
the working tree). Do not state that it is frozen anywhere else.

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
| Corpus, licence, domain | UNRESOLVED | UNRESOLVED |
| Size (lines / words) | UNRESOLVED | UNRESOLVED |
| Gold boundary set (size, annotators, dev/test sizes) | UNRESOLVED | UNRESOLVED |
| ZWNJ annotation sample | UNRESOLVED | UNRESOLVED |
| Analyzer (name, version, licence) | UNRESOLVED | UNRESOLVED |

Splits: content-hashed line splits 80/10/10 (salt fixed in `configs/data/*.yaml`); gold
types split dev/test by type. Test annotations are never used for tuning.

## 4. Primary outcome

* **Primary metric:** micro boundary F1 over gold word types in stripped coordinates
  (`src/morphtok/eval/morph_boundary.py`), on the **test** gold split, at each
  preregistered vocabulary size.
* **Primary contrast:** `unigram_soft − unigram` and `unigram_soft − unigram_hard`.
* **Success threshold (minimum F1 gain):** UNRESOLVED — to be set from pilot variance.
* **Maximum acceptable fertility increase:** UNRESOLVED.

## 5. Secondary outcomes

Exact-match accuracy; fertility (tokens per raw orthographic word); tokens per stripped
character; mean token length; frequency-stratified and coverage-stratified F1;
normalization share; sampling entropy; (Gate 5) downstream metrics.

## 6. Analysis plan

* Vocabulary sizes: UNRESOLVED (pilot); every system at the same sizes; realised sizes
  recorded and mismatches reported.
* Seeds: ≥ 3 (UNRESOLVED final number from pilot variance); seeds vary the training
  subsample and resampling.
* Uncertainty: paired bootstrap (1000 resamples) over gold types for F1 and over lines
  for fertility; approximate randomization test; t-interval over per-seed deltas;
  Cohen's d_z over seeds.
* Multiple comparisons: UNRESOLVED (choose Holm–Bonferroni or report all with
  uncorrected CIs, decided before test evaluation).
* Hyperparameters (λ, penalty mapping, min_confidence) selected on **dev only**.
* Every run, including failed ones, is in `runs/ledger.jsonl`.

## 7. Exploratory vs confirmatory

Everything run before the freeze tag is **pilot/exploratory**. Synthetic-data runs are
integration tests and are never evidence for any hypothesis.

## 8. Deviations

Recorded in `prereg/AMENDMENTS.md`.
