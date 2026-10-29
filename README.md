# MorphoTok-SD-UR

A falsification-first research framework for testing whether morphology-aware and
ZWNJ-aware tokenization helps Sindhi and Urdu. Its aim is to find out whether that
works, not to show that it does.

> **Status (2026-10-29 pilot, exploratory; see [`docs/findings_pilot.md`](docs/findings_pilot.md)).**
> Gates 0–3 have run on Sindhi and Urdu Wikipedia and web text, with silver morphology
> derived from UD/UniMorph lemmas and human ZWNJ annotation from Zia et al. (2018).
> 1. ZWNJ is nearly absent from real text (≈3–10 per 100k words) although normative
>    annotation uses it ≈6 times per 100 words. ZWNJ policies change fertility by ≤ 0.1%.
> 2. Boundary supervision used **only during training** improves segmentation of **unseen
>    lemmas** in both languages (+0.01 to +0.04 F1, 3 seeds; also at 4× data), and a
>    fertility-matched random-boundary control does not reproduce it.
> 3. Hard supervision ≥ soft prior (the λ curve rises monotonically to the hard limit).
> 4. On a token-bigram proxy the gain does not transfer (0.2–0.6% worse bits/char).
>
> **No algorithmic novelty:** the method is posterior regularization with a fixed dual
> (Ganchev et al. 2010), and its hard limit is morphological pre-segmentation. Evaluation
> uses silver data on dev splits only; the preregistration is not frozen. See
> [`HONESTY.md`](HONESTY.md) and `prereg/claim_ledger.md`.

Real-data pilot: download the files listed in `data/raw/SOURCE.md`, run `make real-data`
(prepares pilots, silver supervision and the Zia gold), then e.g.
`python scripts/make_targets.py intrinsic --data sindhi --config configs/run/pilot_wiki.yaml`.

## Quick start

```bash
make setup        # python3.11 -m venv .venv + pinned deps (requirements-dev.lock) + editable install
make lint test    # ruff + pytest
make gate1        # ZWNJ/format-character audit + stratified annotation sheet
make gate0        # BPE / Unigram / char x {preserve, remove, boundary_marker}, matched vocab
make gate2        # analyzer coverage; prints NO REAL ANALYZER CONFIGURED when none is set
make tokenizer    # train all configured tokenizers x vocab sizes x seeds
make intrinsic    # boundary F1, fertility, paired CIs, soft-vs-hard, normalization share
make ablations    # lambda / penalty / analyzer-noise / random-boundary control / sampling
make clean
```

Every target uses `DATA=synthetic` by default; `make gate0 DATA=urdu` uses the Urdu
config and fails loudly until a corpus is configured. Without `make` (e.g. on Windows):
`python scripts/make_targets.py gate0 --data synthetic`.

## What the framework does

```
raw text ──NFC──▶ canonical words ──ZWNJ policy──▶ pre-tokens ──tokenizer(+constraints)──▶ tokens
                        │                                              ▲
                        └──strip ZWNJ/ZWJ──▶ analyzer ──confidence──▶ MANDATORY/PREFERRED/FORBIDDEN/UNKNOWN
evaluation: boundaries mapped back to format-stripped coordinates; fertility over raw orthographic words
```

* **Reference Unigram lattice** (`src/morphtok/tokenizers/lattice_unigram.py`): forward,
  backward, Viterbi, k-best, forward-filter/backward-sample, entropy diagnostic, EM training
  to an exact vocabulary size, optional per-edge soft costs and hard exclusions. The maths
  and the soft-to-hard limit are written out in [`docs/lattice.md`](docs/lattice.md).
* **Constraint layer** (`constraints.py`): four boundary types with explicit confidence;
  positions with no analyzer output are `UNKNOWN`, never `FORBIDDEN`.
* **Unicode audit** (`unicode_audit/`): ZWNJ, ZWJ and every other `Cf` character counted
  *separately*, by neighbour class, position in the word, run length and normalization
  form. Joining classes are reported `UNAVAILABLE` unless you supply `ArabicShaping.txt`.
* **Analyzers** (`analyzers/`): an abstract interface, a provenance-enforcing rule engine
  that ships with no rules, a stub Urdu FST wrapper, perturbation and random-boundary
  wrappers, calibration (ECE), and a synthetic-only oracle that refuses real data.
* **Metrics & statistics** (`eval/`): explicit denominators; paired bootstrap,
  approximate randomization, Cohen's d_z, t-intervals over seeds, Wilson intervals; failed
  runs are counted.
* **Experiment registry** (`configs/experiments/registry.yaml`): 12 specifications across
  families A–G. Each one must answer the six mandatory questions or it is rejected on load.
* **Objective registry + novelty screen** (`configs/experiments/objectives.yaml`,
  [`docs/novelty_screening.md`](docs/novelty_screening.md)): an objective cannot be
  labelled `contribution` until its seven-step screen is complete.
* **Provenance**: every run writes a JSON record (`schemas/result.schema.json`) with git
  commit/dirty state, prereg freeze status, config/data hashes, environment and
  warnings, and appends it to `runs/ledger.jsonl`, including failed and skipped runs.
* **Follow-up generator** (`experiments/followups.py`): turns measured patterns into
  `proposed` hypotheses (`schemas/hypothesis.schema.json`); it never promotes them to claims.
* **Preregistration** (`prereg/`): hypotheses, gates 0–5 and a claim ledger, with every
  threshold `UNRESOLVED` until a pilot exists. `make prereg-freeze` refuses a dirty tree
  and creates a `prereg-vN` tag. `make prereg-status` verifies the freeze rather than
  assuming it.

## The first experiment that could falsify the central premise

**Gate 0 on a real corpus** (`make gate0 DATA=urdu` or `DATA=sindhi`) needs only raw text,
with no analyzer and no annotation. It compares `unigram`, `unigram_zwnj_norm` and the
`boundary_marker` policy at matched vocabulary sizes over 3 seeds. Then `make intrinsic`
reports the **normalization share**, Δ(zwnj_norm − unigram) / Δ(soft − unigram). If ZWNJ
removal alone accounts for the fertility difference, the ZWNJ-loss claim is dropped
(Gate 0) before any analyzer work. The same corpus run of `make gate1` produces the
stratified annotation sheet for H2. That is the cheapest next step, and it needs about 200
annotated occurrences rather than a full gold set.

Two measurement artefacts the framework already guards against, both demonstrated on
synthetic data only:

* the `boundary_marker` policy forces a boundary at every ZWNJ, so boundary F1 rises
  "for free" wherever ZWNJ coincides with a morpheme join;
* removing ZWNJ deletes characters, so tokens per word falls mechanically. That is why
  fertility is never treated as evidence of a better tokenizer on its own.

## Adding real resources

1. Put the corpus in `data/raw/`, write `data/raw/SOURCE.md` (URL, licence, date, SHA-256),
   and set `corpus.path` and `corpus.licence` in `configs/data/<lang>.yaml`.
2. Run Gates 0 and 1; annotate the sheet using [`audit/annotation_guidelines.md`](audit/annotation_guidelines.md).
3. Build dev/test boundary gold (`audit/sampling_protocol.md`) and configure an analyzer
   (`analyzer.rules_path` or `analyzer.command`); run Gate 2.
4. Run the pilot, fill in thresholds in `prereg/`, commit, then `make prereg-freeze`.
5. Only then run `04_intrinsic_eval.py --split test --final`. On real data it refuses if
   the prereg is not frozen.

## Layout

```
configs/      data, tokenizer, eval, run, experiments (registry + objectives)
src/morphtok/ data · unicode_audit · analyzers · tokenizers · eval · downstream · experiments
scripts/      00–05 gate scripts, prereg_freeze.py, make_targets.py
prereg/       PREREG, claim ledger, decision gates, amendments
audit/        annotation guidelines, sampling protocol, agreement.py
docs/         lattice maths, objectives, novelty screening
schemas/      result and hypothesis JSON schemas
data/         empty by design (see data/README.md)
tests/        unit + synthetic integration tests; tests/fixtures/synthetic/
```

The exact required tree is present; files added beyond it, and the reasons, are listed in
`HONESTY.md`.
