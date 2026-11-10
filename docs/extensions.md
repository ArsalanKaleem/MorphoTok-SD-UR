# Extensions: what this project can grow into (researched 2026-11-09)

## 1. The deferred experiment: does the tokenizer gain matter downstream? (Gate 5 / H7)

> **Status 2026-11-09:** built and preregistered (`PREREG.md` §9, Amendment 2, tag `prereg-v3`):
> `scripts/14_export_lm_data.py`, `scripts/lm_gate5.py`, `scripts/15_lm_report.py`; Kaggle steps in
> `docs/kaggle_lm_tutorial.md`. **Run 2026-11-09: no transfer; repeated on the full corpora 2026-11-10 (§11): no transfer
> in 6/6 cells** (`docs/findings_lm.md`).

Planned since the pilot (`findings_pilot.md` §9 step 3; `combined_plan.md` phase P4) and still
open: H7 has only a token-bigram proxy, which was 0.2–0.6% *worse* for the supervised
tokenizer. The real test is a small neural language model.

**Design (as built).** Kaggle T4; a ~4M-parameter, 4-layer transformer LM trained from
scratch on the 5,000-line Wikipedia pilot of each language with each tokenizer (`unigram`,
`unigram_hard_trainonly`, `bpe`) at V = 2000 and 4000, 3 seeds, the same token-window recipe
and early stopping on dev; metric bits per character on held-out text (comparable across
tokenizers), plus bits/char on words of held-out lemmas. sdnorm preprocessing is not part of
this study (the tokenizers were trained on unnormalized text). Roughly 1 GPU-hour per language
(estimate).

**Why it is worth doing.** Recent work disagrees on whether morphological alignment
transfers to language modelling:
* Telugu: the tokenizer *algorithm* (BPE vs Unigram) mattered more downstream than
  morphological alignment ([arXiv 2508.08424](https://arxiv.org/abs/2508.08424)).
* Quechua (QuechuaTok): Unigram had the lowest perplexity while the morphology-aware tokenizer
  had the best boundary accuracy, but perplexity came from a bigram model
  ([arXiv 2606.23943](https://arxiv.org/html/2606.23943)).
* BabyLM 2025: morphology-aware tokenizers generalized better on small data
  ([ACL Anthology](https://preview.aclanthology.org/ingest-emnlp/2025.babylm-main.35.pdf));
  Latin: morphology-guided tokenization helped four downstream tasks
  ([arXiv 2511.09709](https://arxiv.org/abs/2511.09709)); Ge'ez-script languages: intrinsic
  gains without MT gains ([arXiv 2509.08812](https://arxiv.org/abs/2509.08812v1)).

No controlled neural-LM result exists for Sindhi or Urdu. Either outcome is reportable: a
transfer, or a confirmed intrinsic/extrinsic gap with a preregistered intrinsic gain.

## 2. The tool: sdnorm (built; `docs/sdnorm.md`)

A search found no Sindhi normalizer for mixed-keyboard text. Existing tools target Urdu
([urduhack](https://urduhack.readthedocs.io/en/latest/_modules/urduhack/normalization/character.html),
[urdunorm](https://pypi.org/project/urdunorm/), [CLE Urdu normalization](https://www.cle.org.pk/Downloads/langproc/urdu_components/Urdu_Normalization_APP_v1.0.pdf))
or convert legacy Sindhi fonts to Unicode
([AMBILE converter](https://ambile.pk/news-updates/as-sindhi-text-to-unicode-converter-launched/)).
Sindhi needs per-word decisions because ک and ڪ are both letters
([r12a Sindhi script notes](https://r12a.github.io/scripts/arab/sd)).
Possible next steps: a pip package, a Hugging Face `tokenizers` pre-normalizer, a small web
demo, and measuring tagger accuracy after normalization.

## 3. A small Sindhi resource release

The native review produced three small datasets that do not exist elsewhere: 267 morpheme-
segmented Sindhi words, 109 labelled ZWNJ occurrences, and 150 spelling-variant judgements.
They derive from Wikipedia and UD (both CC BY-SA), so they can be released under CC BY-SA
with attribution, as a data card listing one annotator and the AI-assisted pass that was
excluded.

## 4. Not recommended

* More languages before Gate 5: it would widen claims that already rest on one domain.
* Training a Sindhi transformer from scratch for classification: the XLM-R result shows
  pretrained encoders already absorb the unseen-lemma benefit.
