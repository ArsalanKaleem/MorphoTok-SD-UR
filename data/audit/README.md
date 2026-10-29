Empty by design in the repository. See ../README.md.

Locally, `review/` holds the native-speaker review sheets created by
`python scripts/make_review_sheets.py` (or `make review-sheets`):

| File | Task |
|---|---|
| `review/<lang>_boundaries.tsv` | morpheme boundaries for 300 held-out word types |
| `review/<lang>_zwnj.tsv` | label each ZWNJ occurrence (MORPH / ORTHO / AMBIG / ERROR / FOREIGN) |
| `review/<lang>_letter_variants.tsv` | SAME / DIFFERENT / UNSURE for spelling pairs |

Instructions: `audit/REVIEWING.md`. Check and import with `python scripts/ingest_review.py`.
These sheets contain corpus text and annotator work, so they are git-ignored and never
committed.
