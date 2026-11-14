# Findings from native-speaker review (Sindhi, 2026-11-09)

Exploratory; dev splits only; preregistration **not** frozen. Urdu has no human review yet.

## 0. Provenance of the labels

| Source | Status | Used as evidence? |
|---|---|---|
| Collaborator's return, all three Sindhi sheets (2026-11-08) | made **with an AI tool** (confirmed by the project owner); a second return copied it with boilerplate notes (556/559 identical decisions) | **No.** Kept only to measure AI–native agreement |
| Project owner (native Sindhi speaker, "AK"), boundaries | by hand; mechanical fixes (empty status on segmented rows → `OK`, case, a typo); AK then corrected 8 rows | Yes |
| AK, ZWNJ pass 1 | by hand (`data/audit/review/history/sd_zwnj_AK_pass1.tsv`) | Yes (reported) |
| AK, ZWNJ pass 2 | 11 labels changed after review; each changed row says so in `note` | Yes (reported next to pass 1) |
| AK, letter variants | by hand | Yes |

Single annotator: no inter-annotator agreement (κ) yet. Label files are git-ignored
(`data/gold/sd_human_dev.tsv`, `data/gold/sd_approved_variants.tsv`); metric outputs are in
`results/human_gold/`.

## 1. Silver boundaries are noisy

On the 267 reviewed dev words (124 with ≥ 1 boundary, 132 boundaries), the lemma-derived
silver labels score **P = 0.553, R = 0.477, F1 = 0.512** against the human labels. They find
about half of the real boundaries, and about half of what they mark is wrong. Every earlier
silver-based F1 is therefore a noisy proxy (H3).

## 2. Re-scoring the pilot tokenizers against human gold

`python scripts/10_human_gold_eval.py --config configs/run/pilot_wiki.yaml --data sindhi --human data/gold/sd_human_dev.tsv`
→ `results/human_gold/report_sd.md`. The same trained models as `SD-EVAL-*` (5,000-line
Wikipedia pilot, 3 seeds); all 267 words belong to lemmas unseen by train-only supervision.

Δ boundary F1 vs plain `unigram` (mean over 3 seeds, 95% t-interval over seed deltas):

| System | V | vs human gold | vs silver, same words |
|---|---|---|---|
| `unigram_hard_trainonly` | 2000 | +0.001 [−0.006, +0.008] | +0.018 [−0.003, +0.040] |
| `unigram_hard_trainonly` | 4000 | **+0.022 [+0.002, +0.043]** | +0.034 [−0.010, +0.079] |
| `unigram_soft_trainonly` | 2000 | −0.001 [−0.006, +0.003] | +0.009 [−0.009, +0.028] |
| `unigram_soft_trainonly` | 4000 | +0.002 [−0.009, +0.013] | +0.008 [+0.003, +0.012] |
| `bpe` | 4000 | −0.084 [−0.107, −0.060] | −0.095 [−0.111, −0.079] |
| `char` | 4000 | −0.108 [−0.136, −0.080] | −0.035 [−0.044, −0.026] |

* The train-only supervision gain **survives native gold at V = 4000** (CI now excludes 0)
  and **disappears at V = 2000**. The silver evaluation overstated it at V = 2000.
* The soft prior has no detectable effect against human gold; hard ≥ soft still holds.
* `*_hard` and `*_hard_trainonly` are identical here, as expected: the inference-time analyzer
  covers no dev lemma.
* Absolute agreement with morphology is low for every system (F1 0.25–0.35; precision
  0.12–0.25): subword tokenizers split far more often than morphology does.
* n = 267 words, one annotator, one domain, one corpus size.

## 3. ZWNJ in real Sindhi text (H2)

109 sampled occurrences from Sindhi Wikipedia. MORPH rate = MORPH / (MORPH + ORTHO + AMBIG);
ERROR and FOREIGN are excluded.

| Labels | FOREIGN | ERROR | AMBIG | ORTHO | MORPH | MORPH rate (Wilson 95%) |
|---|---|---|---|---|---|---|
| AI-assisted return (not evidence) | 65 | 27 | 15 | 0 | 2 | 2/17 = 0.12 |
| AK pass 1 | 67 | 18 | 6 | 6 | 12 | 12/24 = 0.50 (0.31, 0.69) |
| AK pass 2 | 66 | 26 | 4 | 0 | 13 | **13/17 = 0.76 (0.53, 0.90)** |

* 85–92 of 109 occurrences are not Sindhi-internal at all: Persian passages quoted in
  articles (FOREIGN) or stray characters next to spaces and punctuation (ERROR).
* When a ZWNJ does sit inside Sindhi text, it is usually at a **compound or Arabic ال-name
  join**: 9 of the 13 MORPH rows are ال-names (رمضان‌المبارڪ ×3, شمس‌الدين ×5, ربيع‌الاول), the
  rest compounds (بين‌الاقوامي, سلطان‌اولياء, رسول‌زاده, اسلام‌آباد). Only about 7 distinct
  word types: repeated names inflate the token count.
* The earlier claim "ZWNJ is morphological in a minority of occurrences" is **contradicted**
  for the occurrences that are real Sindhi text. ZWNJ is still too rare to matter for
  fertility (finding 1 of `findings_pilot.md` is unchanged).
* The AI-assisted labels disagreed with the native labels on 28/109 rows (pass 1), mostly by
  calling ال-names AMBIG: the AI pass would have reversed this finding.

## 4. Letter variants and the spelling-robustness test (C2)

150 pairs: 126 SAME, 13 DIFFERENT, 11 UNSURE. Patterns in the native judgements:

* Arabic yeh ي → Farsi yeh ی: SAME in 30 of 31 single-letter pairs; DIFFERENT for کي/کی
  (کی is the Urdu word "of").
* keheh ک vs Sindhi kaf ڪ: SAME when the ک-form is not a word (ڪتاب/کتاب, ملڪ/ملک),
  DIFFERENT when it is another real word (کي/ڪي, ڪو/کو, ڪن/کن).
* The three heh shapes are mostly SAME; ته/تہ and ته/تھ are DIFFERENT. Some yeh-barree
  (ے) forms that are Urdu words were marked SAME (سے, رہے, بے); kept as judged.

The confusable test substitutes ي → ی. Re-scored using only approved substitutions (231 کي
tokens removed, 4,280 kept) from the stored per-token results, no retraining:
`python scripts/11_confusable_approved.py --lang sd` → `results/human_gold/confusable_sd.md`.

* Character input still sharply reduces the confusable-substitution drop vs `word`, e.g. at
  the 10% budget: `char` −0.331 [−0.471, −0.190], `gated_unigram_hard_trainonly`
  −0.298 [−0.479, −0.117], `gated_bpe` −0.279 [−0.406, −0.152] (5 seeds).
* For character-aware systems the confusable drop is smaller than the random-letter drop;
  for `word` they are equal (0.494 vs 0.490 at 10%).
* At 100% budget only 3 seeds exist and all intervals include 0 except `sub_unigram_hard_trainonly`.
* Removing the کي tokens changes CPU drops by only 0.00–0.04. XLM-R results store no
  per-token bits, so they were not re-scored.

## 5. What remains

**Scope decision (2026-11-09):** no Urdu review and no second annotator are planned. Urdu
results stay silver-only; Sindhi results rest on one annotator and report no κ.

1. More human boundary words, for power at V = 2000 and on more lemmas (optional).
2. Optional Kaggle rerun saving per-token bits, to re-score XLM-R with approved substitutions.
