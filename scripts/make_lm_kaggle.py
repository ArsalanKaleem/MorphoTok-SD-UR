# ruff: noqa: E501
"""Build the Gate 5 Kaggle package: data zips and a notebook that embeds ``lm_gate5.py``.

    python scripts/make_lm_kaggle.py --out ../kaggle_upload
    python scripts/make_lm_kaggle.py --out ../kaggle_upload/lm_full --study full   # PREREG §11

Writes ``sd_lm.zip``, ``ur_lm.zip`` (the ``.npz`` streams and ``meta.json`` from
``scripts/14_export_lm_data.py``; token ids only, no text) and ``morphtok_lm_kaggle.ipynb``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def md(text: str) -> dict:
    """Markdown cell."""
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(keepends=True)}


def code(text: str) -> dict:
    """Code cell."""
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
            "source": text.strip("\n").splitlines(keepends=True)}  # fmt: skip


def main() -> int:
    """Write the package."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--study", choices=["pilot", "full"], default="pilot")
    a = ap.parse_args()
    full = a.study == "full"
    sub, sfx = ("lm_full", "_full") if full else ("lm", "")
    smoke_stem = "unigram_V4000_s0" if full else "unigram_V2000_s0"
    est = (
        "estimate: 3–5 hours per language on a T4; not measured"
        if full
        else "estimate: roughly 1 hour per language on a T4; not measured"
    )
    run_langs = (
        'RUN_LANGS = ["sd"]  # first version: ["sd"]; second version: ["ur"]\n'
        if full
        else 'RUN_LANGS = ["sd", "ur"]\n'
    )
    a.out.mkdir(parents=True, exist_ok=True)
    for lang in ("sd", "ur"):
        src = ROOT / "data" / "tasks" / sub / lang
        z = a.out / f"{lang}_lm{sfx}.zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_STORED) as zf:  # npz files are already compressed
            for f in sorted(src.iterdir()):
                zf.write(f, f"{lang}_lm{sfx}/{f.name}")
        print(
            f"{z}: {z.stat().st_size / 1e6:.1f} MB, sha256 {hashlib.sha256(z.read_bytes()).hexdigest()[:16]}"
        )
    script = (ROOT / "scripts" / "lm_gate5.py").read_text(encoding="utf-8")
    header = (
        md("""
# MorphoTok-SD-UR: full-corpus language-model study (Kaggle T4)

Same question and recipe as the Gate 5 pilot, now with LMs that have enough text: the
full-corpus tokenizers (`unigram` vs `unigram_hard_trainonly`; V = 4000, 8000, 16000;
3 seeds) and up to 150,000 training lines per language. **18 small transformer LMs per
language**, scored in bits per character on held-out text. The analysis rule was fixed
beforehand (`prereg/PREREG.md` §11, tag `prereg-v7`).

**Before running:** Settings → Accelerator **GPU T4 x1**. Internet is not needed. Add the
private datasets `sd-lm-full` and `ur-lm-full` via *Add Input*.

**Run one language per version** (each fits well inside Kaggle's 12-hour limit): set
`RUN_LANGS` in section 5, then *Save & Run All*. Outputs: `results_lm_sd.jsonl` /
`results_lm_ur.jsonl` in the Output tab, one line per run.
""")
        if full
        else None
    )
    cells = [
        header
        or md("""
# MorphoTok-SD-UR: Gate 5 language-model study (Kaggle T4)

Does the tokenizer that won the preregistered intrinsic test (`unigram_hard_trainonly`)
also give a better **language model** than plain `unigram`? (`bpe` is a secondary baseline.)

For each language: 3 tokenizers × 2 vocabulary sizes × 3 seeds = **18 small transformer LMs**,
same architecture and recipe, scored in **bits per character** on held-out text.
The analysis rule was fixed beforehand (`prereg/PREREG.md` §9, tag `prereg-v3`).

**Before running:** Settings → Accelerator **GPU T4 x1**. Internet is not needed. Add the
private datasets `sd-lm` and `ur-lm` via *Add Input*.

**Outputs** (`/kaggle/working`, Output tab): `results_lm_sd.jsonl`, `results_lm_ur.jsonl`,
one line per run. Re-running a cell resumes: finished runs are skipped.
"""),
        md("## 1. Check the GPU"),
        code("""
import torch
print("torch", torch.__version__, "| CUDA:", torch.cuda.is_available())
print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NO GPU: Settings -> Accelerator -> GPU T4 x1")
"""),
        md("## 2. Write the experiment script (identical to `scripts/lm_gate5.py` in the repository)"),
        code("%%writefile lm_gate5.py\n" + script),
        md("## 3. Find the uploaded data folders (identified by `meta.json`)"),
        code("""
import glob, json, os
DATA = {}
for meta in glob.glob("/kaggle/input/**/meta.json", recursive=True):
    DATA[json.load(open(meta, encoding="utf-8"))["lang"]] = os.path.dirname(meta)
print(DATA)
assert DATA, "no data found: attach the LM datasets via 'Add Input'"
"""),
        md("""
## 4. Smoke test (about 1 minute)

One tokenizer, 200 steps, written to a separate folder. `test bpc` should be roughly
3–6 and must not be `nan`. If this cell fails, copy the error and stop.
"""),
        code(f"""
lang = "sd" if "sd" in DATA else "ur"
!python lm_gate5.py --data {{DATA[lang]}} --lang {{lang}} --out smoke --only {smoke_stem} --max-steps 200 --min-steps 100 --eval-every 100
"""),
        md(f"""
## 5. Full runs ({est})

Best started with **Save Version → Save & Run All (Commit)** so it keeps running with the
browser closed. Sindhi first, then Urdu.
"""),
        code(
            run_langs
            + """
for lang in RUN_LANGS:
    if lang in DATA:
        !python lm_gate5.py --data {DATA[lang]} --lang {lang} --out .
    else:
        print(lang, "dataset not attached: skipped")
"""
        ),
        md("## 6. Quick look (the paired analysis is done locally with `scripts/15_lm_report.py`)"),
        code("""
import pandas as pd
for f in ("results_lm_sd.jsonl", "results_lm_ur.jsonl"):
    if os.path.exists(f):
        df = pd.read_json(f, lines=True)
        print("\\n==", f, "| runs:", len(df), "| skipped steps:", int(df["skipped_steps"].sum()))
        print(df.groupby(["vocab", "tokenizer"])[["test_bpc", "test_bpc_heldout_lemma", "steps"]].agg(["mean", "std"]).round(4).to_string())
"""),
    ]
    nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                        "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}  # fmt: skip
    p = a.out / f"morphtok_lm{sfx}_kaggle.ipynb"
    p.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
