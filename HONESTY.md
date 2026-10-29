# HONESTY — what exists, what does not, and what has not been tested

Last audited: 2026-10-29 (overnight real-data pilot). Results summary: `docs/findings_pilot.md`.

## 1. Resources

**Obtained, with provenance (`data/raw/SOURCE.md`: URLs, hashes, licences as stated by each source):**
* Sindhi and Urdu Wikipedia (dump 2023-11-01; CC BY-SA 3.0 / GFDL), encyclopedia domain.
* FineWeb-2 test splits for `snd_Arab` and `urd_Arab` (ODC-By 1.0 + Common Crawl terms), web domain.
* UD_Sindhi-Isra (CC BY-SA 4.0; news and folk stories) and UD_Urdu-UDTB (**CC BY-NC-SA 4.0**,
  non-commercial) treebanks: manual lemmas, used to *derive* silver boundaries.
* UniMorph Urdu (CC BY-SA 3.0; licence taken from the UniMorph dataset script, not re-checked on the repo).
* Zia et al. 2018 Urdu segmentation corpus (CC BY 4.0): **human** ZWNJ sub-word annotation.

None of these files is committed. Not verified: Wikipedia text extraction details, and
per-page language (only an Arabic-*script* filter is applied). The Leipzig Corpora
Collection was not used because its pages are behind an anti-bot challenge.

**Gold vs silver.** `data/gold/{sd,ur}_silver.tsv` is **silver**: boundaries derived by a
heuristic (stem = longest common prefix of form and lemma) from manual lemma
annotations, split by lemma. It is not linguistically validated segmentation.
`data/gold/ur_zia_zwnj.tsv` is human annotation, but only of ZWNJ-marked sub-word
boundaries, so only recall is meaningful against it.

**Still missing:** a human inflectional boundary gold set, labels for the ZWNJ annotation
sheets, any rule-based or FST analyzer, a Unicode joining-class file, and native-speaker
review of anything.

**Review tooling exists, but no labels have been collected yet (2026-10-30).**
`scripts/make_review_sheets.py` wrote the boundary, ZWNJ and letter-variant sheets for
both languages to `data/audit/review/` (local, git-ignored), and
`scripts/ingest_review.py` validates and imports them. The importer is tested on
synthetic rows only. Nothing produced from these sheets is in any result yet.

## 1a. Real-data pilot results (exploratory; dev splits; prereg NOT frozen)

Summarised in `docs/findings_pilot.md`, with run IDs. In short:
* ZWNJ is nearly absent in real Sindhi and Urdu text (encyclopedia, web, news), although
  normative annotation places it at about 5.8 per 100 words. ZWNJ policies change
  fertility by ≤ 0.1%.
* Silver boundary supervision used **only during training** improves segmentation of
  **lemmas it never covered** (Sindhi +0.019/+0.039 F1, Urdu +0.011/+0.014 at V = 2000/4000,
  3 seeds). A fertility-matched random-boundary control does not reproduce it.
* Hard supervision beats the soft prior at λ = 2. Normative ZWNJ supervision barely
  helps compounds, because plain Unigram already recovers 91–93% of them.
* The method is posterior regularization with a fixed dual: **no algorithmic novelty**
  (`docs/novelty_screening.md`).

## 2. Implemented and unit-tested (hand-computed or exhaustive oracles)

| Component | Tests |
|---|---|
| Unigram lattice: forward/backward, log Z, edge marginals, Viterbi, k-best, FFBS sampling, entropy, empty and unreachable inputs | `test_lattice_sampling.py` (vs exhaustive enumeration) |
| Soft costs = violation cost; hard posterior = restriction to the feasible set; soft → hard as λ grows; soft ≠ hard when infeasible | `test_lattice_sampling.py`, `test_constraints.py` |
| EM trainer reaches the exact vocabulary size and keeps every character | `test_lattice_sampling.py` |
| Constraint semantics (UNKNOWN default, PREFERRED never hard, edge decomposition) | `test_constraints.py` (exhaustive over boundary sets) |
| Normalization policies, index maps, stripped-coordinate evaluation | `test_unicode.py` |
| Format-character audit, joining-table parser, ZWNJ occurrences and oracle labels | `test_unicode.py` |
| Fertility, tokens/char, boundary P/R/F1, exact match, frequency bins, bootstrap, approximate randomization, d_z, seed aggregation, Wilson CI, Cohen/Fleiss κ, ECE | `test_metrics.py`, `test_constraints.py` |
| Splits: deterministic, duplicate-safe, dev/test gold disjoint; real data never substituted | `test_splits.py` |
| Registry and objective validation, novelty gate, result records and ledger, follow-up triggers | `test_synthetic_corpus.py` |
| BPE/Unigram/char baselines through the full pipeline on the synthetic fixture; incremental BPE = naive reference | `test_synthetic_corpus.py` |
| Lemma-derived silver boundaries, lemma splits, merging sources, paradigm coherence | `test_paradigm_silver.py` (hand-computed) |

Status: see the final audit at the bottom of `docs/findings_pilot.md` (tests and lint re-run after the overnight changes), `ruff check` and `ruff format --check` are clean.

## 3. Exercised on synthetic data, and now also on real pilot data

All numbered scripts (00–06), the ablation grid, sampling stability, the perturbation and
random-boundary wrappers, the follow-up generator and the bigram bits-per-character proxy
have run on the synthetic fixture **and** on the real Sindhi/Urdu pilots. The data-prep
scripts (`prepare_wikipedia.py`, `build_silver.py`, `build_zia_gold.py`,
`codepoint_variants.py`) have only been run on the real files, not unit-tested.

**Synthetic numbers are not findings.** The fixture is an invented Latin-letter
"language" (80 stems, 3 prefixes, 8 suffixes, ZWNJ inserted by fixed probabilities), and
its "analyzer" is the generator's own gold. Every synthetic experiment ID starts with
`SYN-`, and every script prints a SYNTHETIC banner. What the synthetic runs do show is
that the instruments can detect confounds: the random-boundary control recovered part of
the gain, `boundary_marker` raised F1 at no cost, and plain Unigram's F1 fell with word
frequency. These are properties of the generator and the code, not of either language.

## 4. Stubs (interfaces only; raise or return "unavailable")

* `analyzers/fst_urdu.py`: subprocess plumbing only; `parse_output` raises
  `NotImplementedError` because no output format has been verified.
* `analyzers/rules_sindhi.py`: a generic affix engine that ships with **no rules**. Rules
  without provenance are rejected.
* `downstream/sentiment.py`, `downstream/ner.py` (the `run` methods): no dataset. NER
  label alignment *is* implemented and tested.
* `downstream/lm_small.py`: neural LM not implemented. The bigram proxy is implemented
  and is **not** a language-model result.
* `downstream/adapt.py`: generic decomposition-mean initialisation. It is **not** claimed
  to be FOCUS or FVT, neither of which has been verified.
* Objective D's λ_z prior and Objective F's entropy term are **not implemented**
  (`configs/experiments/objectives.yaml`).
* Joining classes: `UNAVAILABLE` unless an `ArabicShaping.txt` path is supplied.
* `selective` ZWNJ policy: no approved rules exist, so it behaves as `preserve` and warns.

## 5. Claims

H1, H2, H4, H5 and H6 have **pilot-only** evidence; H3 and H7 are untested or have only
a proxy (`prereg/claim_ledger.md`). Novelty: **no algorithmic novelty is claimed**.
Objective A was screened and is posterior regularization with a fixed dual; Objective B
is morphological pre-segmentation. Any contribution is empirical or resource-level and
has not been screened for prior *empirical* work on Sindhi/Urdu.

## 6. Modelling choices that are assumptions, not facts

* Ambiguous analyses are aggregated as weighted alternatives (`aggregate`); this is uncalibrated.
* Format characters attach to the left piece when analyzer boundaries are mapped into
  `preserve`-policy strings (`format_char_attach: left`).
* Boundary metrics use format-stripped coordinates; fertility uses raw whitespace words.
* The pruning loss is an approximation; whether it matches any published procedure is unverified.
* Between-seed variation comes from a 90% training subsample (the algorithms are
  deterministic); this is one choice of nuisance variation among several.
* `lambda: 2.0` and the trainer settings in `configs/tokenizer/*.yaml` are **pilot**
  values chosen for CPU speed on the synthetic fixture, not tuned values.
* The stratified ZWNJ sample is not reweighted to corpus proportions yet (TODO in
  `audit/sampling_protocol.md`).

## 7. Environment deviations from the specification

* **Python:** the spec requires 3.11. Only **CPython 3.14.7** was available, so all tests
  and runs used 3.14.7. `requires-python = ">=3.11"`, and no 3.11-only feature is
  avoided or used knowingly, but **3.11 has not been tested**.
* **make:** not installed on the development machine (Windows 11), so **the Makefile was
  not executed**. `scripts/make_targets.py` runs the same commands, and every target was
  run through it.
* **uv / pip-tools:** neither was available. The lock files were written from `pip
  freeze` of the working environment in pip-tools format, and were not produced by
  `pip-compile`.
* **pre-commit:** installed (4.7.0) and configured with local hooks, but **the hooks have
  not been run**: the git repository was initialised with no commits.
* **pyarrow** (26.0.0) reads the parquet dumps. It is pinned as the optional `[data]` extra
  and in `requirements-data.lock`.
* **Performance:** BPE was rewritten with incremental pair counts (tested to give the same
  merges as the naive version); it takes about 1 s per training on a 290k-word pilot.
  Unigram EM takes about 10–15 s on the same pilot. Real corpora will need profiling or a verified library backend
  (TODO in `tokenizers/baselines.py`).

## 8. Provenance and preregistration state

The repository has been `git init`-ed with **no commits**, so every run record has
`git.commit = null` with a warning. **The preregistration is not frozen**: no
`prereg-v*` tag exists, and `make prereg-status` reports `frozen: False`.

## 9. Files added beyond the required tree (and why)

| File | Reason |
|---|---|
| `src/morphtok/__init__.py` and subpackage `__init__.py` files | package importability |
| `src/morphtok/{config,provenance}.py` | config hashing and run provenance (Part II) |
| `src/morphtok/experiments/{registry,results,followups,objectives,runner}.py` | experiment registry, results schema, discovery schema, objective registry, shared run logic (Parts III, IV, XI) |
| `src/morphtok/tokenizers/pipeline.py` | one composition of normalization, analyzer and tokenizer shared by every script |
| `src/morphtok/analyzers/synthetic.py` | synthetic-only oracle for integration tests |
| `src/morphtok/data/synthetic.py`, `tests/fixtures/synthetic/*` | the deterministic 1,000-line synthetic corpus (Part IX) |
| `configs/data/synthetic.yaml`, `configs/tokenizer/char.yaml` | synthetic dataset config; character-level control (Family B) |
| `configs/experiments/{registry,objectives}.yaml` | machine-readable registries |
| `docs/{lattice,objectives,novelty_screening}.md` | derivations and novelty workflow (Part IV allows `docs/`) |
| `schemas/*.json` | results and hypothesis schemas (deliverables 12, 13) |
| `prereg/AMENDMENTS.md`, `scripts/prereg_freeze.py` | freeze and amendment mechanism |
| `scripts/make_targets.py` | runs the Makefile targets where `make` is unavailable |
| `scripts/prepare_wikipedia.py`, `configs/data/*_audit.yaml`, `configs/run/pilot_wiki.yaml`, `data/raw/SOURCE.md` | turn the Wikipedia parquet dumps into pilot text files with provenance; full-text audit configs; real-data vocabulary sizes |
| `src/morphtok/analyzers/lemma_derived.py`, `src/morphtok/eval/paradigm.py`, `tests/test_paradigm_silver.py` | silver supervision from manual lemmas; paradigm-coherence metric |
| `scripts/{build_silver,build_zia_gold,codepoint_variants,06_lm_proxy}.py` | silver/gold construction, orthographic variant audit, Gate 5 proxy |
| `configs/data/{sindhi,urdu}_{web,web_audit,randctrl,20k}.yaml`, `configs/data/urdu_zia*.yaml`, `configs/tokenizer/*_trainonly.yaml`, `configs/eval/intrinsic_silver.yaml`, `configs/run/pilot_{zia,ctrl,scale}.yaml` | domain, negative-control, scale and train-only conditions |
| `docs/findings_pilot.md` | pilot report |
| `scripts/{make_review_sheets,ingest_review}.py`, `audit/REVIEWING.md`, `tests/test_review.py` | native-speaker review workflow |
| `tests/conftest.py`, `data/*/README.md`, `.gitignore`, `requirements*.lock` | test import path, documented empty directories, hygiene, pinned dependencies |
