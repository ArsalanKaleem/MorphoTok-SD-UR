# Novelty-screening workflow

Mandatory before implementing, or describing as new, any objective or algorithm.
Enforced in code: `NoveltyScreen.may_claim_novelty()` in
`src/morphtok/experiments/objectives.py` returns `True` only when all seven steps are
recorded, `equivalence_to_known_method` is `false`, and `sources_verified` is non-empty.
An objective with status `contribution` and an incomplete screen fails to load.

## Steps (record each in the objective's `novelty_screen` block)

1. **closest_existing_formulation**: the closest published formulation, cited from
   `CITATIONS.md` (verified entries only).
2. **term_by_term_comparison**: both objectives in the same notation, every term compared.
3. **equivalence_to_known_method**: `true` if the optimisation problem is equivalent
   (including up to reparameterisation) to a known method.
4. **terminology_search**: search terms, venues and dates.
5. **smallest_new_element**: the minimal component not covered by steps 1–4.
6. **isolating_baseline**: a baseline identical except for that element.
7. **disproving_result**: the result that would show the element is not useful.

## Screen log (2026-10-29)

Searches run (web search, standard and extended modes), plus full reads of the key PDFs (ganchev2010 pp. 2006–2009, kohonen2010 pp. 78–81): "morphologically informed
unigram tokenization constrained segmentation lattice morpheme boundaries 2024 2025";
"subword regularization morpheme boundary prior unigram language model EM penalty
lattice linguistic constraints"; "tokenizer evaluation morphological alignment metric
paradigm consistency MorphScore"; "Urdu tokenizer subword morphology evaluation paper
ZWNJ". Primary pages were checked for every work cited below (`CITATIONS.md`).

### Objective B: hard constraints. **Equivalent to a known method.**

* Closest: morphological pre-segmentation before subword training (brahma2025 for
  BPE; vemula2025 for BPE and Unigram).
* Term by term: with MANDATORY constraints only, removing every lattice edge that spans
  a mandatory position yields exactly the lattice of the word split at those positions.
  So EM training and Viterbi decoding are identical to running Unigram on the
  pre-segmented pieces. FORBIDDEN constraints have no pre-segmentation analogue, but no
  experiment uses them.
* Equivalence: **true** (for the configuration used). B stays a *reference* baseline.
  It is our implementation of "pre-segmentation for Unigram", which vemula2025 report
  helps BPE but not Unigram.

### Objective A: soft, confidence-weighted boundary prior in Unigram EM. **Equivalent to a known method.**

* **Posterior regularization (ganchev2010), read from the JMLR PDF.** Proposition 2.1
  (Eq. 5) gives the PR E-step projection as `q*(Y) ∝ p_θ(Y|X)·exp(−λ*·φ(X,Y))`.
  Proposition 2.2 says it factors when φ factors over cliques. The modified EM (Eq. 8)
  keeps the M-step unchanged, and §2.3 notes that the projected `q` can be used for
  prediction.
* **Term by term.** Our soft training E-step computes `P(s|w) ∝ p(s|w)·exp(−λ·V(s))`
  with `V(s)` factored over lattice edges, then runs the ordinary Unigram M-step. That
  is the PR E′-step with constraint feature `φ = V` and a **fixed** λ, where PR solves
  for the dual `λ*` that meets a bound `b`; the penalised/slack form of PR (§2.3) has the
  same structure. Decoding with constraints (`decode_mode: soft`) is PR's prediction
  with the projected `q`.
* **Semi-supervised Morfessor (kohonen2010), read from the PDF.** Gold analyses enter as
  a β-weighted likelihood term, with α on the unlabeled likelihood (Eq. 8), and labeled
  words' analyses are restricted to their gold alternatives. That is the hard limit of
  our prior plus a reweighting. Close in spirit (a unigram morph lexicon with a few gold
  analyses), different in mechanism.
* **Equivalence: true.** Objective A is an instance of PR. **No algorithmic novelty is
  claimed.**
* **What remains open is empirical, not algorithmic.** Does PR-style boundary
  supervision of a Unigram *tokenizer* vocabulary generalize to words the supervision
  never covered (held-out lemmas; compounds whose ZWNJ is absent in real text), at
  matched vocabulary, and does it beat the random-boundary control? Results:
  `docs/findings_pilot.md`.

### Paradigm-coherence metric (`eval/paradigm.py`). **Screen incomplete.**

* Closest: MorphScore (arnett2025coling, arnett2025morph70) scores per-word alignment of
  token boundaries with morpheme boundaries. Coherence instead asks whether *all forms of
  a lemma* share one stem tokenization, which needs only paradigms, not segmentations.
* Not yet checked: whether the 70-language MorphScore release or other work measures
  cross-form consistency. Treat it as a diagnostic, not a contribution.

### Objectives C–G

Not started (see `configs/experiments/objectives.yaml`).
