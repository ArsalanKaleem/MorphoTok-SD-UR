# How to review the sheets

Six sheets, two per task (`sd_` = Sindhi, `ur_` = Urdu). Do the language(s) you are
native in. They live in `data/audit/review/` (local only; never committed).

**Editing:** open each `.tsv` in **LibreOffice Calc** or **Google Sheets**, or in Excel via
*Data → From Text/CSV*, delimiter **Tab**, encoding **UTF-8**. Save back as **tab-separated
text in UTF-8**, keeping the file name. A plain text editor such as VS Code also works:
columns are separated by single tabs. Do not reorder or delete rows or columns.

Work in short sessions and keep your own judgement: nothing in a sheet is a "correct
answer" to agree with. When you finish (or pause), run

    python scripts/ingest_review.py

It checks every row and tells you exactly which rows have problems.

---

## Task 1: morpheme boundaries (`sd_boundaries.tsv`, `ur_boundaries.tsv`), about 300 words each

This is the most important task. It replaces the automatically derived ("silver") labels
behind the main result.

* `word`: the word, as written in the corpus.
* `segmentation`: **pre-filled with the word itself. Insert `+` wherever one morpheme
  ends and the next begins.** Change nothing else: the letters must stay exactly the same,
  and the checker rejects any row whose letters changed.
  * Mark all morpheme boundaries you see: stem | inflectional ending, prefixes, suffixes,
    stacked suffixes, compound members.
  * A word with no internal boundary: leave it unchanged (no `+`).
  * Format example (not a claim about these particular words): a word `ABCDE` that you
    analyse as stem `ABC` + ending `DE` becomes `ABC+DE`; stem + two endings becomes
    `ABC+D+E`.
* `status`: **fill this in for every row you review.** Rows with an empty status count as
  not reviewed, so you can stop at any point.
  * `OK`: you are confident (including words with no internal boundary, left unchanged).
  * `?`: you are not confident (e.g. several analyses are possible). Put the
    alternative in `note` (for example `alt: AB+CDE`).
  * `SKIP`: not a word of the language (a name in another language, a typo, an
    abbreviation). Say why in `note`.
* `context`: one sentence fragment where the word occurs (may be empty). Use it to tell
  apart homographs.

## Task 2: ZWNJ occurrences (`sd_zwnj.tsv`, 109 rows; `ur_zwnj.tsv`, 236 rows)

Each row is one place where a ZWNJ (zero-width non-joiner) occurs in Wikipedia. In
`right_context` it is shown as `<ZWNJ>`; `left_context` is the text just before it.

Fill `label` with exactly one of:

| Label | Use when |
|---|---|
| `MORPH` | the ZWNJ sits at a morpheme boundary (e.g. between compound members, or stem and affix) |
| `ORTHO` | it is only there for spelling or shaping, not at a morpheme boundary |
| `AMBIG` | you cannot decide |
| `ERROR` | it looks like a typing or encoding mistake |
| `FOREIGN` | the text around it is not Sindhi/Urdu (e.g. Persian or Arabic quoted inside an article) |

Put your initials in `annotator` (or leave it empty, which counts as `A1`). Use `note`
for anything else. If a second native speaker can label the same file independently,
duplicate each row with their initials, and the checker will compute agreement (κ).

## Task 3: letter variants (`ur_letter_variants.tsv`, `sd_letter_variants.tsv`), 150 pairs each

Each row is a **pair** of spellings that differ only in yeh / kaf / heh letters (for
example Arabic yeh ي vs Farsi yeh ی), with how often each occurs in Wikipedia.
`spelling_A` is the more frequent one, and `letters that differ` shows exactly which
letters change. Judge each pair on its own: the same word may appear in several rows.

Fill `decision` with exactly one of:

| Decision | Use when |
|---|---|
| `SAME` | A and B are the same word; the difference is only an encoding or keyboard variant |
| `DIFFERENT` | A and B are different words (or the letters are genuinely different letters in this language) |
| `UNSURE` | you cannot decide |

In `note`, say which spelling is standard when it is `SAME`. For **Sindhi**, remember that
several of these letters are distinct letters of the Sindhi alphabet, so `DIFFERENT` may be
common there. That is exactly what we need to know.

---

## What happens with your answers

* Task 1 → `data/gold/<lang>_human_dev.tsv`, the first **human** gold set. The pilot result
  (supervision helps unseen words) is re-evaluated against it, and the silver labels'
  precision is measured.
* Task 2 → the ZWNJ morphology rate (H2) with a confidence interval, from actual usage.
* Task 3 → a list of approved letter equivalences, the only normalization the data showed
  has measurable reach. It is applied only if you mark it `SAME`.
