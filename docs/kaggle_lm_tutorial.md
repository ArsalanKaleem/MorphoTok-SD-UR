# Gate 5 on Kaggle: step-by-step

What this runs: 36 small language models (18 Sindhi, 18 Urdu), one per tokenizer × vocabulary
size × seed, to test whether the preregistered tokenizer gain carries over to language
modelling. Estimated GPU time: about 1 hour per language on a T4 (estimate, not measured).

Files in this folder:

| File | What it is |
|---|---|
| `sd_lm.zip` (16 MB) | Sindhi token-id streams: 18 `.npz` files + `meta.json` (numbers only, no text) |
| `ur_lm.zip` (11 MB) | Urdu, same layout |
| `morphtok_lm_kaggle.ipynb` | the notebook; it writes `lm_gate5.py` itself |

## 1. Upload the two datasets (once)

1. kaggle.com → **Create → New Dataset**.
2. Drag in `sd_lm.zip`. Title: **sd-lm**. Visibility: **Private**. **Create**.
3. Repeat with `ur_lm.zip`, title **ur-lm**, Private.

Kaggle unzips them; that is expected.

## 2. Open the notebook

1. **Create → New Notebook → File → Import Notebook** → choose `morphtok_lm_kaggle.ipynb`.
2. Right panel → **Session options**: Accelerator **GPU T4 x1**. Internet can stay off.
3. Right panel → **Add Input** → *Your Datasets* → add **sd-lm** and **ur-lm**.

## 3. Check, then smoke-test

1. Run cell 1: it must print `CUDA: True` and `Tesla T4`.
2. Run cells 2 and 3: cell 3 must print both paths, e.g. `{'sd': '/kaggle/input/sd-lm/sd_lm', 'ur': ...}`.
3. Run cell 4 (smoke test, about 1 minute). The last line looks like
   `unigram_V2000_s0: test bpc 4.1 ... steps 200`. Any number roughly 3–6 is fine;
   `nan` or an error means stop and send me the message.

## 4. Full run

Click **Save Version → Save & Run All (Commit) → Save**. It keeps running with the browser
closed. Progress: *View → Logs* of the running version; each finished model prints one line.

If the session stops early, just commit again: finished runs are skipped.

## 5. Bring the results back

1. When the version shows **Complete**, open it → **Output** tab.
2. Download `results_lm_sd.jsonl` and `results_lm_ur.jsonl` (and, for provenance,
   `lm_gate5.py`).
3. Put them in `C:\Projects\Morph\kaggle_upload\results\` and tell me "LM results are in".

I will then check provenance (the downloaded `lm_gate5.py` must equal the repository copy,
apart from the final newline), run `scripts/15_lm_report.py` for both languages, apply the
preregistered rule (transfer / harm / no detectable effect), and update the claim ledger.

## What the numbers mean

* **bpc (bits per character):** how many bits the model needs per character of held-out
  text. Lower is better; it is comparable across tokenizers because every tokenizer
  encodes exactly the same characters.
* **held-out-lemma bpc:** the same, only on words whose lemma the tokenizer's morphology
  supervision never saw, the place where a transfer should show first.
