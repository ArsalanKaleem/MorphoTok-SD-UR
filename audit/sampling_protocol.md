# Sampling protocol

Implemented in `src/morphtok/unicode_audit/contexts.py` and `scripts/00_zwnj_audit.py`.

## ZWNJ occurrences (Gate 1)

* **Frame:** every run of consecutive U+200C characters in the NFC-normalized corpus
  (a run counts once; run length is recorded in the audit).
* **Strata:** `(left-neighbour class, right-neighbour class, position in word)`, where a
  class is Unicode general category plus the first word of the character name (a
  reporting label, not a script lookup) and position ∈ {initial, medial, final, isolated}.
* **Allocation:** proportional to stratum size with a minimum of 1 item per stratum
  (`stratified_sample`); seed fixed in `configs/run/default.yaml: gate1.sample_seed`.
  Because of the per-stratum minimum the realised sample can exceed `sample_size`.
* **Estimation:** strata are reported separately. The pooled MORPH rate is a rate over the
  *sample*; if strata are over-sampled relative to the corpus, a stratum-weighted estimate
  must be reported alongside it (TODO: implement weighting before Gate 1 on real data).
* **Sheet columns:** `occ_id, stratum, word, char_index, left_context, right_context,
  label, annotator, note`. One row per (occurrence, annotator); duplicate the row for each
  annotator.

## Boundary gold (Gates 2–3)

* **Frame:** stripped word types of the corpus.
* **Strata:** training-frequency bins (`configs/eval/intrinsic.yaml: frequency_bins`) ×
  ZWNJ-present/absent × analyzer covered/uncovered (when an analyzer exists).
* **Split:** each sampled type is assigned dev/test by a salted hash of the type (the same
  rule as `morphtok.data.synthetic.gold_split`) before annotation.
* **File format** (`data/gold/<lang>_gold.tsv`):
  `word<TAB>boundaries<TAB>source<TAB>split`, boundaries as comma-separated positions in
  the stripped word; lines starting with `#` are comments.
* **Sample sizes:** UNRESOLVED until a pilot estimate of F1 variance is available.
