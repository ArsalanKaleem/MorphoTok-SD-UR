# Combined plan: where should morphological information enter?

**Status (2026-11-05):** Phase 1 (evaluation sets) is done. A CPU-scale version of Phases 3–4
(BiLSTM taggers, not XLM-R) has run for both languages: results in `docs/findings_pos.md`.
The XLM-R experiment (`scripts/xlmr_fusion.py`) is written but has not run; it needs a T4.
Decisions taken: Sindhi primary, Urdu replication, UD-only data, this repository. It merges
the tokenizer study (this repository) with the character–subword fusion proposal into
one question, and reuses the pilot's evaluation splits.

## 1. Research question

For Sindhi (primary) and Urdu (secondary), does morphological information help more when
it enters through the **tokenizer** (segmentation) or through the **model input**
(character features fused with subword embeddings)? And does any gain come from
**morphological generalization** or only from **spelling robustness**?

The second half is the scientific core. A model can look better because it copes with
orthographic variants, or because it generalizes to unseen inflected forms. These need
different evaluation sets, which is what this repository already provides.

## 2. Hypotheses (all untested; thresholds UNRESOLVED until the pilot)

| ID | Statement |
|---|---|
| C1 | Character–subword fusion improves POS accuracy over XLM-R fine-tuning on tokens whose **lemma is unseen** in training. |
| C2 | Fusion improves robustness to **approved spelling variants** (native-speaker `SAME` pairs) more than to random character noise. |
| C3 | The fusion gain is largest in low-data budgets (1–10% of the labelled training set) and shrinks with more data. |
| C4 | A gated fusion beats a plain concatenation with the same parameter count (otherwise the gate is unnecessary complexity). |
| C5 | Tokenizer-level supervision (`unigram_hard_trainonly`) and model-level character features help *different* subsets (unseen lemmas vs spelling variants). |

Prior pilot evidence relevant to C5: morphology-aware segmentation improved intrinsic
unseen-lemma segmentation but *not* a bigram LM proxy (`docs/findings_pilot.md`).

## 3. Data: what is verified (2026-11-04)

| Resource | Task | Status | Licence |
|---|---|---|---|
| UD Sindhi-Isra (in `data/raw/ud/`) | POS (UPOS, manual), lemmas | **downloaded, verified**; ≈90k tokens, news and folk stories | CC BY-SA 4.0 |
| UD Urdu-UDTB (in `data/raw/ud/`) | POS, lemmas | **downloaded, verified**; ≈138k tokens | CC BY-NC-SA 4.0 (research only) |
| SiPOS (Ali, Xu & Kumar, RANLP-SRW 2021) | POS, 16 UPOS tags, ≈293k tokens, Kawish/Awami-Awaz news | paper verified on the ACL Anthology; **data link `github.com/AliWazir/SiPOS-Dataset` returns 404** → contact the authors | unknown |
| Sindhi news articles (Daily Kawish; `rajavavek/SindMT` CSV, Kaggle `owaisraza009/sindhi-articles-dataset-from-daily-kawish`) | topic classification (3 classes in the linked code) | located, **not downloaded**; size and licence unverified | **unknown**, blocker for publication |
| Sindhi Wikipedia + FineWeb-2 (in `data/raw/`) | optional domain-adaptive MLM | downloaded | CC BY-SA / ODC-By |
| "SdCorpus" | (proposal) | **not found** under that name; Wikipedia/FineWeb-2 replace it | — |

**Novelty warning, from the SiPOS paper itself:** its best baseline (96.25%) already
*combines word- and character-level representations*. Character + word fusion for
Sindhi POS is therefore not new. The contribution must be the *diagnostic* (C1 vs C2), the
tokenizer-vs-model comparison (C5) and the low-resource curves (C3), screened as in
`docs/novelty_screening.md` before any claim.

## 4. Evaluation sets (built from existing repository data)

1. **Standard UD dev/test** (as released).
2. **Unseen-lemma subset:** test tokens whose lemma never occurs in the training split
   (computed from UD lemmas; same idea as the pilot's held-out-lemma split).
3. **Spelling-variant perturbation:** test sentences where words are replaced by their
   approved `SAME` variant (from your review sheet `sd_letter_variants.tsv`), plus a
   **random-character-noise control** with the same number of edits.
4. **Low-data budgets:** 1%, 5%, 10%, 25%, 50%, 100% of the training sentences (nested
   subsets, fixed seeds).

## 5. Systems

| System | What it isolates |
|---|---|
| XLM-R base, standard fine-tuning | baseline |
| XLM-R + character CNN, **concatenation** (parameter-matched) | character information without a gate |
| XLM-R + character CNN, **gated fusion** (the proposal) | the gate (C4) |
| Small transformer from scratch with `unigram` tokenizer | tokenizer baseline at small scale |
| Same, with `unigram_hard_trainonly` tokenizer | tokenizer-level morphology (C5) |
| Same + character CNN | both together |

Optional: mBERT and DistilXLM-R as extra baselines if compute allows.

**Controls:** ≥3 seeds per cell (5 for the 1–10% budgets); parameter-matched variants;
identical hyperparameter search budget per system on dev only; test evaluated once after
a preregistration amendment freezes thresholds.

## 6. Compute (single T4, ~16 GB)

XLM-R base fine-tuning on ≈90k tokens takes minutes per run. The main grid is
3 fusion variants × 6 budgets × 3–5 seeds ≈ 60–90 runs, roughly 1–2 GPU-days. The
from-scratch small transformers are also feasible on a T4. **Not yet estimated by
measurement.**

## 7. Phases and decision gates

| Phase | Work | Gate to continue |
|---|---|---|
| P0 | Decide datasets (UD-only vs also SiPOS/news); request SiPOS; check news licence | at least one POS set with a known licence (UD Sindhi already satisfies this) |
| P1 | Build evaluation sets 2–4 from UD; finish native review Tasks 1 and 3 | unseen-lemma subset ≥ UNRESOLVED tokens; ≥ UNRESOLVED approved variant pairs |
| P2 | XLM-R baselines across budgets | baseline variance measured → set thresholds, amend prereg |
| P3 | Concatenation and gated fusion | C4: if gate ≤ concat, drop the gate |
| P4 | Tokenizer-level systems (small transformer) | C5 comparison |
| P5 | Analysis: C1 vs C2 split, rare words, error analysis by native speaker | — |
| P6 | Novelty screen on the final claims; write-up | claims survive the screen |

## 8. Decisions needed from the project owner

1. **Scope:** Sindhi only, or Sindhi + Urdu (the Urdu treebank is non-commercial)?
2. **Datasets:** UD Sindhi-Isra only (available now), or also pursue SiPOS (email the
   authors) and the Kawish news set (licence must be established)?
3. **Task 2 (ZWNJ labels):** keep or deprioritise? It no longer feeds the main question.
   Tasks 1 (boundaries) and 3 (letter variants) now matter most.
4. **Repository:** extend this repository with a `src/morphtok/models/` module (recommended:
   shared splits, ledger and statistics), or start a separate one?
