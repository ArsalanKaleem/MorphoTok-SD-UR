# XLM-R fusion results (Kaggle T4, 2026-11-08)

Metric-only outputs of `scripts/xlmr_fusion.py`, one JSON line per run. They contain no
corpus text, so they are committed.

| File | Runs | SHA-256 |
|---|---|---|
| `results_sd.jsonl` | 27 (base/concat/gated × budgets 0.01/0.1/1 × seeds 0–2) | `06fe130065b382d189b9d5666929c42ada1a81a3202e0dc034109cc178473fdb` |
| `results_ur.jsonl` | 27 (same grid) | `60fd1350d58551b011e628b093e9edeb0c4e47b61d03658b9b6f0863b531d177` |
| `smoke_sd.jsonl` | 2 (smoke test: base, gated; budget 0.01; seed 0) | not used in analysis |

**Provenance**
* Script: the copy downloaded from the Kaggle output is byte-identical to
  `scripts/xlmr_fusion.py` at commit `90da788` (SHA-256 of the Kaggle copy:
  `5590ecae9f54ec204d95b629b8a97ffac24ea906ce555ed43183127fca22526c`).
* Model: `xlm-roberta-base`, Hugging Face commit `e73636d4f797dec63c3081bb6ed5c7b0bb3f2089`
  (from Kaggle's `__huggingface_repos__.json`).
* Data: `data/tasks/{sd,ur}_pos/` uploaded as private Kaggle datasets (`kaggle_upload/*.zip`,
  byte-identical to the local task files).
* Hardware: Kaggle T4, fp16 autocast. Skipped (non-finite) optimizer steps: Sindhi 66 of
  25,732, Urdu 57 of 17,399 (≈0.3%, normal GradScaler warm-up).
* GPU time: Sindhi 1.72 h, Urdu 1.34 h (sum of per-run seconds).

Report: `python scripts/09_xlmr_report.py --lang sd|ur` (writes `report_<lang>.md` here).
