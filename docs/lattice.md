# Reference Unigram lattice: definitions

Implementation: `src/morphtok/tokenizers/lattice_unigram.py`, `constraints.py`, `sampling.py`.
Tests: `tests/test_lattice_sampling.py`, `tests/test_constraints.py`.

This is a transparent reference implementation. The equations below are standard
Unigram-LM machinery with one added, edge-decomposable cost. **No novelty is claimed**;
see `docs/novelty_screening.md`.

## Objects

For a word `w` of length `n`, a *candidate edge* `e = [i, j)` exists when `w[i:j]` is in
the vocabulary (or `j = i + 1`, through the explicit unknown-character edge with finite
log-probability `unk_logp`). A segmentation `s` is a path `0 → n`; `B(s) ⊆ {1..n−1}` is its
set of interior boundaries.

| Quantity | Definition | Code |
|---|---|---|
| per-edge score | `φ(e) = log p(e) − λ c(e)` | `Edge.score` |
| violation cost | `V(s) = Σ_{e∈s} c(e) = Σ_k ([k∉B(s)] a_k + [k∈B(s)] f_k)` | `WordConstraints.violation_cost` |
| segmentation posterior | `P_{λ,α}(s|w) = exp(α Σ_{e∈s} φ(e)) / Z_{λ,α}(w)` | `Lattice.sample` |
| partition function | `Z_{λ,α}(w) = Σ_{s∈S_valid(w)} exp(α Σ φ(e))` | `Lattice.log_partition` |
| training objective | `max_{log p} Σ_w f(w) log Z_{λ,1}(w)` (EM, constraints fixed) | `UnigramTrainer` |
| decoding objective | `argmax_s Σ_{e∈s} φ(e)` (independent of α > 0) | `Lattice.viterbi` |

`a_k` (absent-boundary cost) is `π(c_k)` for MANDATORY and PREFERRED evidence; `f_k`
(present-boundary cost) is `π(c_k)` for FORBIDDEN evidence; UNKNOWN positions cost 0.
`π` maps confidence to nats (`linear`, `log_odds`, `threshold`, `uniform`).

### Edge decomposition

Edge `[i, j)` makes positions `i+1 … j−1` absent and position `j` present (if `j < n`), so

    c([i, j)) = Σ_{k=i+1}^{j−1} a_k + [j < n] f_j,

and summing over a path's edges gives exactly `V(s)`. Forward, backward, Viterbi, k-best
and forward-filter/backward-sample therefore remain exact; `test_edge_costs_sum_to_violation_cost`
checks this exhaustively.

### Hard constraints

HARD mode removes edges that span a MANDATORY position or end at a FORBIDDEN one. This is
the only place a weight is `−∞`. The feasible set is

    F(w) = { s : MANDATORY ⊆ B(s) and FORBIDDEN ∩ B(s) = ∅ }.

PREFERRED evidence is never a hard exclusion. If `F(w) = ∅` the lattice has no complete
path: `log_partition` raises `NoValidSegmentationError`; `encode` either raises
`InfeasibleConstraintsError` (`fallback="error"`) or decodes without constraints
(`fallback="unconstrained"`), and training counts every fallback.

### When does soft converge to hard?

With soft costs on **the same** MANDATORY/FORBIDDEN set and `π(c_k) > 0` for all of them,
`V(s) = 0 ⇔ s ∈ F(w)`. If `F(w) ≠ ∅`, as `λ → ∞` the weight of every infeasible path
vanishes relative to feasible ones, and feasible paths keep their relative weights, so
`P_λ → P_hard` (`test_soft_large_lambda_converges_to_hard`). The limit fails when:

1. `F(w) = ∅` — soft concentrates on minimum-violation paths; hard has no distribution
   (`test_soft_limit_differs_from_hard_when_infeasible`);
2. some `π(c_k) = 0` (e.g. `threshold` below τ, `log_odds` with `c ≤ 0.5`) — that constraint
   is never enforced;
3. PREFERRED evidence is included in the soft run — it is enforced in the limit but is
   never part of the hard feasible set;
4. finite `λ` with log-probability gaps larger than `λ·min π(c_k)` — the LM wins.

### Sampling

`alpha` is an inverse temperature on the whole path score. Samples are drawn by
forward-filter/backward-sample over exactly the lattice's edges, so their distribution
normalises over `S_valid(w)` (`test_sampling_distribution_normalises`).
`Lattice.entropy()` returns `H(P(s|w)) = log Z − α E[Σ φ]` as a **diagnostic only**.

### Training (EM + pruning)

E-step: edge marginals under the (optionally constrained) lattice, weighted by word
frequency. M-step: `p(t) ∝ E[count(t)] + smoothing`. Pruning keeps every character and
removes the pieces whose removal least increases an approximate corpus NLL
(`E[count(t)] · (log p(t) − score of the best alternative segmentation of t)`), shrinking
by at least `shrink` per round until the target size is met **exactly**. The pruning
loss ignores renormalisation; whether it equals any published variant has not been
verified (TODO in the code).

## Numerical safeguards

`logsumexp` handles empty and all-`−∞` inputs; all log-probabilities and `unk_logp` must
be finite (`UnigramModel.__post_init__`); `λ ≥ 0`, `α > 0` are enforced; empty words have
the empty segmentation with `log Z = 0`.
