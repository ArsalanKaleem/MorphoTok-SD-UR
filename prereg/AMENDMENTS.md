# Preregistration amendments

Added beyond the required tree to hold post-freeze changes.

Template for each amendment:

```
## Amendment N — YYYY-MM-DD — tag prereg-vN
- Section changed:
- Old text:
- New text:
- Reason (cite run IDs if motivated by data):
- Was any test-set result seen before this change? yes/no
```

## Amendment 1 — 2026-11-09 — tag prereg-v2
- Section changed: `claim_ledger.md` rows H4 and H5 and its change log (evidence and status
  only). `PREREG.md` and `decision_gates.md` are unchanged.
- Old text: H4/H5 evidence ended with the human-gold dev results; status pilot-only.
- New text: adds the confirmatory test results and sets H4 to supported (hard train-only,
  3/4 tests) and H5 to partly supported.
- Reason: recording the outcome of the preregistered test evaluation
  (`results/final_test/decision.md`, runs `SD-EVAL-*-test`, `UR-EVAL-*-test`). No hypothesis,
  contrast, threshold or analysis was changed.
- Was any test-set result seen before this change? **yes** (this amendment reports them).
- Run provenance: all test runs record commit `a259f86` with `prereg-v1` verified frozen.
  The Urdu runs are flagged `dirty: true` because untracked files of the new `sdnorm` tool
  existed during the run; no tracked file and no evaluation code had changed.
