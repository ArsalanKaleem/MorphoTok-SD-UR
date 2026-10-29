# Annotation guidelines (draft — not yet reviewed by a Sindhi or Urdu linguist)

These guidelines define *procedure*. They do not contain linguistic rules for Sindhi or
Urdu; those must come from qualified annotators and be documented with examples they
supply. No annotation in this repository has been expert-validated.

## 1. Tasks

**Task Z (ZWNJ audit, Gate 1).** For each sampled ZWNJ occurrence
(`zwnj_annotation_sheet.tsv`), assign one label:

| Label | Meaning |
|---|---|
| `MORPH` | The ZWNJ sits at a morphological boundary (between morphemes of one orthographic word). |
| `ORTHO` | The ZWNJ is orthographic only (e.g. controls joining/shaping) and is not at a morpheme boundary. |
| `AMBIG` | The annotator cannot decide from the word and context. |
| `ERROR` | The ZWNJ appears to be an encoding or typing error. |
| `FOREIGN` | The surrounding text is not in the target language (e.g. Persian quoted in an Urdu article). Excluded from the MORPH-rate denominator, like `ERROR`. |

**Task B (boundary gold, Gates 2–3).** For each sampled word type, mark every
morphological boundary as a position in the word *with all ZWNJ/ZWJ removed*
(stripped coordinates; `audit/sampling_protocol.md` gives the tool format). In the
review sheets this is done by inserting `+` between morphemes in the pre-filled
`segmentation` column, and setting `status` to `OK`, `?` (unsure) or `SKIP` (not a word
of the language). Rows without a status count as not yet reviewed. Step-by-step
instructions for reviewers are in `audit/REVIEWING.md`.

**Task V (letter variants).** For each pair of spellings that differ only in yeh, kaf
or heh code points, decide `SAME` (one word, encoding or keyboard variant), `DIFFERENT`
(different words or distinct letters) or `UNSURE`. Only `SAME` pairs may ever become
`selective` normalization rules.

## 2. Morphological vs orthographic boundaries

* A **morphological boundary** separates morphemes (stem, affix, clitic, compound member)
  according to the annotator's analysis. The annotator records which kind in `note`.
* An **orthographic boundary** is any visual or encoding break (space, ZWNJ, non-joining
  letter) that is not a morpheme boundary. Orthographic boundaries are **not** marked in
  Task B.
* The two are annotated independently: a ZWNJ is never evidence by itself.

## 3. Ambiguity

If more than one segmentation is defensible, record the most likely one and list the
alternatives in `note` (`alt=3,5|3`). Do not resolve ambiguity by frequency.

## 4. Procedure

1. Annotators work independently and never see each other's labels.
2. ≥ 2 annotators label at least the overlap subset (size: UNRESOLVED, set in prereg).
3. Agreement: `python audit/agreement.py <sheet>` (Cohen's κ per pair; Fleiss' κ when
   every item has the same number of raters).
4. **Adjudication:** strict majority wins; ties become `AMBIG` and go to an adjudicator,
   whose decision and reason are recorded in a separate column. Original labels are kept.
5. Guideline changes after annotation starts are versioned in this file with a date, and
   items annotated under an older version are flagged.

## 5. Dev/test separation

Word types are assigned to `dev` or `test` by hashed type (`split` column) **before**
annotation. Test annotations are stored separately (`data/gold/*_test.tsv`), are never
used for tuning, and are evaluated only with `04_intrinsic_eval.py --split test --final`
after the preregistration freeze.

## 6. Licensing and privacy

* Record the corpus licence and whether redistribution of annotated contexts is allowed
  before sharing any sheet.
* Contexts may contain personal names or sensitive text; share sheets only with
  annotators covered by the data agreement, and remove contexts before publication if the
  licence requires it.
* Annotator identities are pseudonymised (`A1`, `A2`, …) in released files.
