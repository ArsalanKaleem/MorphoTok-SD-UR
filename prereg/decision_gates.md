# Decision gates 0–5

Thresholds were set on 2026-11-09 **after** the dev pilot, with the dev results known (see
`PREREG.md`). Where a gate was already evaluated on dev, its outcome is recorded as *Pilot
outcome*. Synthetic results never pass or fail a gate.

**Scope decision (2026-11-09):** no Urdu native review and no second annotator are planned.
Gates that require ≥ 2 annotators are evaluated descriptively, for Sindhi only, and cannot
be passed.

Outcomes per gate: **continue** · **revise** · **abandon/pivot**.

## Gate 0 — Baselines and normalization (`make gate0`, registry A1)

* **Minimum data quality:** real corpus with verified licence; ≥ 50,000 words; Unicode
  form fixed (NFC unless the audit shows NFC changes text); duplicate-aware splits.
* **Metrics:** fertility, tokens/char, mean token length, boundary F1 (if gold exists).
* **Analysis:** BPE, Unigram, char × {preserve, remove, boundary_marker} at matched
  vocabulary sizes, ≥3 seeds; paired bootstrap of each policy vs preserve; normalization
  share from `04_intrinsic_eval.py`.
* **Continue:** morphology-aware variants differ from `unigram_zwnj_norm` beyond the
  normalization effect (share < 0.5).
* *Pilot outcome:* ZWNJ policies change fertility by ≤ 0.1%; share ≈ 0 → **continue**.
* **Revise:** normalization share ≥ 0.5 → **remove the ZWNJ-loss claim**; compare
  methods only within one policy.
* **Abandon:** — (Gate 0 alone cannot abandon the project).
* Known artefact: `boundary_marker` forces a boundary at every ZWNJ, so any ZWNJ that
  coincides with a gold boundary is predicted "for free". Report it separately.

## Gate 1 — ZWNJ audit (`make gate1`, registry A2)

* **Minimum data quality:** ≥ 100 adjudicated occurrences; ≥ 2 annotators on ≥ 20% of
  items; κ ≥ 0.6.
* *Pilot outcome (sd):* 109 occurrences, **1 annotator** → minimum data quality **not met**;
  reported descriptively (MORPH 13/17, Wilson (0.53, 0.90)). ur: no annotation.
* **Metrics:** MORPH rate with Wilson 95% CI (AMBIG in the denominator, ERROR excluded);
  per-stratum rates; Cohen/Fleiss κ.
* **Continue (ZWNJ as morphological signal):** CI lower bound ≥ 0.5.
* **Revise (ZWNJ as orthographic/robustness variable only):** CI upper bound <
  0.5 → Objective D only, never ZWNJ-as-morphology supervision.
* **Abandon ZWNJ-morphology claims:** as in Revise.

## Gate 2 — Analyzer coverage (`make gate2`, registry C1)

* **Minimum data quality:** manually reviewed dev gold of ≥ 200 types; analyzer
  version and licence recorded.
* **Metrics:** type and token coverage; boundary P/R/F1 on covered dev gold types; ECE.
* **Continue:** token coverage ≥ 0.20 and boundary precision ≥ 0.70 on reviewed dev gold.
* *Pilot outcome (sd):* token coverage 0.27, precision **0.55** on 267 native-reviewed words
  → **revise** (low precision): supervision is used only during training and the silver-gold
  caveat is reported. ur: precision unmeasured.
* **Revise:** low precision → high-confidence-only supervision / calibration (C2); low
  coverage → coverage-reduction curve to estimate what is needed.
* **Pivot:** no usable analyzer → uncertainty-aware supervision, robustness evaluation, or
  a resource-oriented study (annotated boundary dataset).
* `make gate2` must print "NO REAL ANALYZER CONFIGURED" when none is set.

## Gate 3 — Soft vs hard (`make tokenizer intrinsic ablations`, registry B1, B2, C2, C3, D1, E1)

* **Minimum data quality:** Gates 0–2 passed or explicitly revised; ≥ 3 seeds; matched
  vocabulary verified in every record.
* **Metrics:** primary F1 contrasts with bootstrap CIs and t-CIs over seeds; λ curve;
  perturbation slope; random-boundary control; frequency strata.
* **Continue with soft prior:** soft − hard > +0.005 with CI over seeds excluding 0 on
  dev, then confirmed once on test after the freeze.
* **Revise (simplify):** hard ≥ soft, or the λ curve rises monotonically to the hard limit
  → **keep hard constraints, remove the soft prior**.
* *Pilot outcome:* hard ≥ soft in both languages and both V; the λ curve rises to the hard
  limit → **revise**: the primary contrast is `unigram_hard_trainonly − unigram` (`PREREG.md` §4).
* **Abandon method claim:** neither beats `unigram_zwnj_norm`, or the random-boundary
  control recovers most of the gain.

## Gate 4 — Entropy ablation (registry G2)

* Entered only if Gate 3 evidence documents a specific reason (e.g. a sampling failure).
* Requires Objective F to be fully specified (distribution, sign, effect, relation to α).
* **Keep the term** only with a reproducible benefit over the identical no-entropy
  variant (CI over seeds excluding 0); otherwise drop it.

## Gate 5 — Downstream (registry G1)

* Entered only after Gate 3 passes.
* Controls fixed in `configs/eval/downstream.yaml`; character-budgeted sequences.
* If intrinsic gains do not transfer, **report that distinction**; do not change the
  primary claim.
