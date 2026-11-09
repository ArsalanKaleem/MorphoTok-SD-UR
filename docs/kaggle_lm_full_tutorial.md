# Full-corpus LM study on Kaggle (PREREG §11): step-by-step

What this runs: 36 small language models (18 Sindhi, 18 Urdu): `unigram` vs
`unigram_hard_trainonly`, V = 4000 / 8000 / 16000, 3 seeds, on up to 150,000 training lines
per language. Same model and recipe as the pilot Gate 5 study; only the data is larger.
Estimated GPU time: 3–5 hours per language on a T4 (estimate, not measured).

Files in `C:\Projects\Morph\kaggle_upload\lm_full\`:

| File | What it is |
|---|---|
| `sd_lm_full.zip` | Sindhi token-id streams: 18 `.npz` files + `meta.json` (numbers only, no text) |
| `ur_lm_full.zip` | Urdu, same layout |
| `morphtok_lm_full_kaggle.ipynb` | the notebook; it writes `lm_gate5.py` itself |

## 1. Upload the two datasets (once)

1. kaggle.com → **Create → New Dataset**.
2. Drag in `sd_lm_full.zip`. Title: **sd-lm-full**. Visibility: **Private**. **Create**.
3. Repeat with `ur_lm_full.zip`, title **ur-lm-full**, Private.

## 2. Open the notebook

1. **Create → New Notebook → File → Import Notebook** → choose `morphtok_lm_full_kaggle.ipynb`.
2. Right panel → **Session options**: Accelerator **GPU T4 x1**.
3. **Add Input** → *Your Datasets* → add **sd-lm-full** and **ur-lm-full**.

## 3. Check, then smoke-test (interactive session)

1. Cell 1 must print `CUDA: True` and `Tesla T4`.
2. Cells 2 and 3: cell 3 prints both data paths.
3. Cell 4 (smoke test, 1–2 minutes): last line like `unigram_V4000_s0: test bpc 4.x ...`.
   Roughly 3–6 is fine; `nan` or an error means stop and send me the message.

## 4. Two full runs: one per language

Kaggle stops a run after 12 hours, so each language gets its own version.

1. In section 5, check the first line reads `RUN_LANGS = ["sd"]`.
   **Save Version → Save & Run All (Commit) → Save**.
2. Right away (you do not need to wait), edit that line to `RUN_LANGS = ["ur"]` and save a
   **second** version the same way. If Kaggle refuses to run two at once, start the second
   after the first shows **Complete**.

Both keep running with the browser closed. Progress: *View → Logs* of each version.

## 5. Bring the results back

From each completed version's **Output** tab download the `.jsonl` file
(`results_lm_sd.jsonl` from the first, `results_lm_ur.jsonl` from the second) and `lm_gate5.py`.
Kaggle's "Download all" zip is fine. Put them in `C:\Projects\Morph\kaggle_upload\lm_full\results\`
and tell me "full LM results are in".
