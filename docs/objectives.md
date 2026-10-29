# Objective registry: derivations and status

Machine-readable registry: `configs/experiments/objectives.yaml` (validated by
`src/morphtok/experiments/objectives.py`). This page gives the reasoning; the YAML is
authoritative for status.

General form, with every term a placeholder that must be defined and justified on its own:

    L = L_base + λ_m L_morph + λ_z L_orth + λ_c L_confidence + λ_r R

Redundancy rule: two terms that express the same preference (e.g. a confidence-weighted
morph term **and** a separate confidence term over the same boundaries) are not allowed.
In the current implementation `L_confidence` is folded into `L_morph` through the
penalty mapping `π(c)`; there is no separate confidence term.

| ID | Name | Status | Implemented | Minimal falsification |
|---|---|---|---|---|
| A | Soft boundary prior | candidate | yes (`train_mode/decode_mode: soft`) | B1, B2 |
| B | Hard constraints | reference | yes (`hard`) | B1 |
| C | Confidence-weighted supervision | candidate | yes (`supervision.penalty`) | C2 penalty stage |
| D | Orthographic ZWNJ prior | candidate | policies only; λ_z prior **not** implemented | A1, A2 |
| E | Alternative sampling | candidate | sampling + diagnostics | E1 |
| F | Entropy term | deferred (Gate 4) | **not** implemented | G2 |
| G | Data-driven alternatives | placeholder | — | defined per follow-up |

## A — Soft boundary prior

This is **not** `L_base + λ E_{P(s|w)}[V(s)]`. The implemented model puts `−λ V(s)`
*inside* the path score, so it changes the model distribution rather than adding an
expectation penalty to the loss. The training objective is
`Σ_w f(w) log Σ_s exp(Σ log p(e) − λ V(s))`, maximised over `log p` by EM. Consequences:

* The gradient w.r.t. `log p(t)` is `E_{P_λ}[count(t)] − (normaliser term)`: pieces
  consistent with constraints receive more expected counts, so the *vocabulary* shifts.
* A posterior-regularisation-style alternative (penalising `E_P[V]` of the *unpenalised*
  posterior) is a different objective; it is not implemented and must be screened
  before implementation.

Units: `λ` is nats per unit penalty; `π(c) ∈ [0, 1]` for `linear`, `[0, ∞)` for `log_odds`.

## B — Hard constraints

Indicator of the feasible set multiplies the path weight (edges removed). The infeasible
case is handled by an explicit fallback that is counted. This is a standard constrained
decoding/training scheme and is a baseline, not a contribution.

## C — Confidence weighting

The test of whether confidence matters is the `uniform` mapping on the *same*
constraint set: if `linear` ≈ `uniform` under realistic noise, confidence weighting adds
nothing. With the synthetic oracle (constant confidence 0.9) the two coincide up to a
rescaling of `λ`, so synthetic runs cannot show a difference by construction.

## D — Orthographic prior

Gate 1 decides whether ZWNJ is mostly orthographic. Only then is a separate boundary class
with its own `λ_z` justified; it must not be merged with analyzer boundaries (double
counting where they coincide).

## E — Sampling

`α` scales the whole path score. If the posterior is near-deterministic at the chosen `α`
(E1), sampling-based arguments are moot.

## F — Entropy (deferred)

Before any implementation, the Gate 4 record must specify: the distribution whose entropy
is measured (per-word `P_λ(s|w)` vs. the corpus unigram `p`), the sign, the optimisation
effect (e.g. adding `+β H(P(s|w))` to a per-word objective flattens posteriors, which may
be equivalent to lowering `α`), and its relation to segmentation diversity. Equivalence to
temperature scaling must be checked first.
