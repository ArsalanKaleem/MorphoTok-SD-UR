# Normalization x POS tagging on Kaggle (PREREG §12): step by step

What this runs: 36 part-of-speech taggers (BiLSTM `word` and `char`) trained with three
normalizers (none, sindhinorm 0.1.0 rules, sindhinorm 0.2.0 keyboard mode) on SiPOS and on UD
Sindhi, 3 seeds each. The design and decision rules were frozen before any result (tags
`prereg-v9`, `prereg-v10`). Estimated time on a T4: under an hour (estimate, not measured).

Files in `C:\Projects\Morph\kaggle_upload\normpos\`:

| File | What it is |
|---|---|
| `sd_normpos.zip` (2 MB) | task files (SiPOS and UD Sindhi) and the code the runner needs |
| `morphtok_normpos_kaggle.ipynb` | the notebook |

**The zip contains SiPOS text, which its authors shared with you privately. Keep the Kaggle
dataset Private.**

## 1. Upload the dataset

1. kaggle.com → **Create → New Dataset**.
2. Drag in `sd_normpos.zip`. Title: **sd-normpos**. Visibility: **Private**. **Create**.

## 2. Open the notebook

1. **Create → New Notebook → File → Import Notebook** → choose `morphtok_normpos_kaggle.ipynb`.
2. Right panel → **Session options**: Accelerator **GPU T4 x1**.
3. **Add Input** → *Your Datasets* → **sd-normpos**.

## 3. Check, then smoke-test

1. Cell 1 must print `CUDA: True` and `Tesla T4`.
2. Cell 2 prints the package path and a long hash.
3. Cell 3 (smoke test, about a minute, dev split only) prints two lines that contain
   `"device": "cuda"`, with `acc_clean` around 0.5 to 0.6. An error or `"device": "cpu"`
   means stop and send me the message.

## 4. Full run

**Save Version → Save & Run All (Commit) → Save**. It keeps running with the browser closed;
each finished run prints one line in the version's log. If the session stops early, commit
again: finished runs are skipped.

## 5. Bring the results back

From the completed version's **Output** tab download everything ("Download all" is fine):
`runs_sipos.jsonl`, `runs_ud_sd.jsonl`, `per_token_sipos.jsonl`, `per_token_ud_sd.jsonl` and
`19_norm_pos.py`. Put them in `C:\Projects\Morph\kaggle_upload\normpos\results\` and tell me
"POS results are in". I will check that the script is identical to the repository version,
apply the preregistered rules with `scripts/20_norm_pos_report.py`, and record the outcome.
