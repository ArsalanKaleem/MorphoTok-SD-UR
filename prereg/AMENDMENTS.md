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

## Amendment 2 — 2026-11-09 — tag prereg-v3
- Section changed: `PREREG.md` new §9 (Gate 5 language-model study). Nothing else changed.
- Old text: none (Gate 5 had controls only in `configs/eval/downstream.yaml`).
- New text: §9 fixes the data, model recipe, metric, primary contrast and decision rule.
- Reason: specify the downstream test before it is run on Kaggle.
- Was any test-set result seen before this change? Tokenizer test results yes (Amendment 1);
  **no language-model result of any kind** (none has been run).

## Amendment 3 — 2026-11-09 — tag prereg-v4
- Section changed: `PREREG.md` new §10 (full-corpus scale-up). Nothing else changed.
- Old text: none.
- New text: §10 fixes data, systems, vocabulary sizes, metric, decision rule and prediction.
- Reason: address the main limitation of the confirmatory test (5,000-line corpora) before
  submission.
- Was any test-set result seen before this change? Pilot-scale tokenizer test results yes
  (Amendment 1); **no full-corpus result of any kind**, and no language-model result.

## Amendment 4 — 2026-11-09 — tag prereg-v5
- Section changed: `claim_ledger.md`, row H7 (evidence and status). Nothing else changed.
- Old text: evidence "PROXY only … no neural LM yet"; status "untested (proxy consistent)".
- New text: Gate 5 results added; status "supported" (no transfer in 4/4 primary cells,
  harm in 1).
- Reason: recording the outcome of the Gate 5 study preregistered in §9 (Amendment 2).
  No hypothesis, contrast, threshold or analysis was changed.
- Was any test-set result seen before this change? **yes** (this amendment reports the
  LM test results).
- Run provenance: Kaggle T4, `lm_gate5.py` identical to the repository copy at `prereg-v3`;
  hashes in `docs/findings_lm.md`.

## Amendment 5 — 2026-11-09 — tag prereg-v6
- Section changed: `claim_ledger.md`, row H5 (evidence and status). Nothing else changed.
- Old text: status "partly supported (fails ur V2000 threshold; sd V2000 not supported on
  human dev gold)".
- New text: full-corpus results added; status "supported at full-corpus scale (6/6); pilot-
  scale exceptions remain on record".
- Reason: recording the outcome of the scale-up preregistered in §10 (Amendment 3). No
  hypothesis, contrast, threshold or analysis was changed.
- Was any test-set result seen before this change? **yes** (dev and non-confirmatory test
  results of the full-corpus tokenizers, reported here).
- Run provenance: models in `runs/{SD-sindhi,UR-urdu}_full-models/` (git-ignored), trained
  from commit `9209724` (`prereg-v4`); evaluation `scripts/16_scale_eval.py` (commit
  `0ca29a0`).

## Amendment 6 — 2026-11-09 — tag prereg-v7
- Section changed: `PREREG.md` new §11 (full-corpus language-model study). Nothing else changed.
- Old text: none.
- New text: §11 fixes the tokenizers, data caps, model recipe, metric, decision rule and
  prediction.
- Reason: the §9 LMs were data-limited, which leaves H7 open to the objection that the
  pilot LM could not use better segmentation.
- Was any test-set result seen before this change? §9 LM results yes (Amendment 4) and
  full-corpus tokenizer results yes (Amendment 5); **no full-corpus LM result of any kind**.

## Amendment 7 — 2026-11-10 — tag prereg-v8
- Section changed: `claim_ledger.md`, row H7 (evidence and status). Nothing else changed.
- Old text: status "supported: the intrinsic gain does not transfer to LM bpc (0/4 transfer,
  1/4 small harm); small, data-limited LMs only".
- New text: full-corpus results (§11) added; status "supported: no transfer to LM bpc in any
  of 10 preregistered cells (pilot and full corpus; 1 small pilot harm); small LMs only".
- Reason: recording the outcome of the study preregistered in §11 (Amendment 6). No
  hypothesis, contrast, threshold or analysis was changed.
- Was any test-set result seen before this change? **yes** (this amendment reports the
  full-corpus LM test results).
- Run provenance: Kaggle T4, `lm_gate5.py` identical to the repository copy; data from
  `scripts/14_export_lm_data.py` at `prereg-v7`; hashes in `docs/findings_lm.md`.

## Amendment 8 — 2026-11-22 — tag prereg-v9
- Section changed: `PREREG.md` new §12 (spelling normalization and POS tagging, H9);
  `claim_ledger.md` new row H9 (status untested). Nothing else changed.
- Old text: none.
- New text: §12 fixes the data and split, test conditions, normalizers, taggers, seeds,
  primary contrasts, decision rules, secondary analyses and prediction.
- Reason: test the normalizer downstream, on SiPOS (obtained from its authors) and on UD Sindhi.
- Was any test-set result seen before this change? **No tagger test result.** Seen before
  freezing: SiPOS code-point and normalizer change counts on the whole file, and dev-only
  smoke runs (listed in §12).
- The systems are defined by this commit: sindhinorm 0.2.0 keyboard mode in
  `packages/sindhinorm/src/sindhinorm/core.py`, `scripts/18_build_norm_pos.py`,
  `scripts/19_norm_pos.py`.

## Amendment 9 — 2026-11-22 — tag prereg-v10
- Section changed: `PREREG.md` §12, one added line on compute. Nothing else changed.
- Old text: none (the compute platform was not specified; the grid was started on a 12-core CPU).
- New text: the §12 runs execute on a Kaggle T4 GPU.
- Reason: the CPU grid (started 2026-11-22 15:44, 6 parallel runs) completed **none of its 36
  runs** in about two hours of active computing, plus a sleep of the computer from 17:01 to
  18:18. It was cancelled. No run finished, so no result file, run record or test accuracy
  exists (`results/norm_pos/` absent; no `SD-NORMPOS` entry in `runs/ledger.jsonl`).
- Implementation changes, none affecting the design: `scripts/19_norm_pos.py` gains `--device`
  (GPU when available; batches moved to the device), `--data-root`, and `--out` (plain result
  files plus per-token correctness, used where no git checkout exists) with resume;
  `morphtok.models.tagger.CharCNN` now allocates its output on the input's device (no change
  on CPU). A dev-only smoke run after the change reproduced the earlier dev numbers exactly
  (word tagger, keyboard mode: 0.5749 clean, 0.5301 keyboard-typed).
- Was any test-set result seen before this change? **No.**
- Provenance plan: the Kaggle package records the SHA-256 of `19_norm_pos.py`; the downloaded
  copy of the script must equal the repository version at this tag.

## Amendment 10 — 2026-11-22 — tag prereg-v11
- Section changed: `claim_ledger.md`, row H9 (evidence and status). Nothing else changed.
- Old text: "Not yet run…"; status "untested".
- New text: §12 results added; status "supported".
- Reason: recording the outcome of the study preregistered in §12 (Amendments 8 and 9). No
  hypothesis, contrast, threshold or analysis was changed. `scripts/20_norm_pos_report.py`,
  which applies the §12 rules, was written after the freeze and before any result existed.
- Was any test-set result seen before this change? **yes** (this amendment reports them).
- Run provenance: Kaggle T4, 36 runs on `cuda`; the downloaded working copy of the code and the
  word list are identical to the repository at `prereg-v10` (line endings normalized); hashes
  in `docs/findings_norm_pos.md`.

