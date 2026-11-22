# ruff: noqa: E501
"""Build the Kaggle package for the normalization x POS study (PREREG.md section 12).

    python scripts/make_normpos_kaggle.py --out ../kaggle_upload/normpos

Writes ``sd_normpos.zip`` (the task files from ``scripts/18_build_norm_pos.py`` plus the code the
runner needs: ``scripts/19_norm_pos.py``, ``morphtok.models.tagger`` and the ``sindhinorm`` package)
and ``morphtok_normpos_kaggle.ipynb``. The zip contains SiPOS text, which was shared privately by
its authors: upload it as a **private** Kaggle dataset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = [
    "scripts/19_norm_pos.py",
    "src/morphtok/__init__.py",
    "src/morphtok/models/__init__.py",
    "src/morphtok/models/tagger.py",
]
TASK_FILES = ("train", "dev", "test", "test_keyboard", "test_kbnoise")


def md(text: str) -> dict:
    """Markdown cell."""
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(keepends=True)}


def code(text: str) -> dict:
    """Code cell."""
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
            "source": text.strip("\n").splitlines(keepends=True)}  # fmt: skip


def main() -> int:
    """Write the zip and the notebook."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    z = a.out / "sd_normpos.zip"
    files = {f"normpos/code/{p}": ROOT / p for p in CODE}
    pkg = ROOT / "packages" / "sindhinorm" / "src" / "sindhinorm"
    for f in sorted(pkg.rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts:
            files[f"normpos/code/packages/sindhinorm/src/sindhinorm/{f.relative_to(pkg).as_posix()}"] = f
    for ds in ("sipos", "ud_sd"):
        for name in TASK_FILES:
            files[f"normpos/tasks/{ds}/{name}.jsonl"] = ROOT / "data" / "tasks" / ds / f"{name}.jsonl"
    meta = {
        "study": "PREREG.md section 12",
        "script_sha256": hashlib.sha256((ROOT / CODE[0]).read_bytes()).hexdigest(),
        "files": sorted(files),
    }
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for arc, src in sorted(files.items()):
            zf.write(src, arc)
        zf.writestr("normpos/normpos_meta.json", json.dumps(meta, indent=1))
    print(f"{z}: {z.stat().st_size / 1e6:.1f} MB, {len(files)} files")

    cells = [
        md("""
# MorphoTok-SD-UR: spelling normalization x POS tagging (Kaggle T4)

Does `sindhinorm` help a part-of-speech tagger on Sindhi text typed with an Urdu keyboard, without
harming clean text? Taggers (BiLSTM, `word` and `char`) are trained with three normalizers (none,
0.1.0 rules, 0.2.0 keyboard mode) on SiPOS and on UD Sindhi, 3 seeds each: **36 runs**.
The analysis rule was fixed beforehand (`prereg/PREREG.md` section 12).

**Before running:** Settings → Accelerator **GPU T4 x1**. Add the private dataset `sd-normpos`
via *Add Input*. Internet is not needed.

**Outputs** (Output tab): `runs_sipos.jsonl`, `runs_ud_sd.jsonl`, `per_token_*.jsonl` and a copy of
`19_norm_pos.py`. Re-running resumes: finished runs are skipped.
"""),
        md("## 1. Check the GPU"),
        code("""
import torch
print("torch", torch.__version__, "| CUDA:", torch.cuda.is_available())
print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NO GPU: Settings -> Accelerator -> GPU T4 x1")
"""),
        md("## 2. Find the uploaded package (identified by `normpos_meta.json`)"),
        code("""
import glob, json, os, shutil
metas = glob.glob("/kaggle/input/**/normpos_meta.json", recursive=True)
assert metas, "dataset not found: add the sd-normpos dataset via 'Add Input'"
PKG = os.path.dirname(metas[0])
print("package:", PKG)
shutil.copy(os.path.join(PKG, "code/scripts/19_norm_pos.py"), "/kaggle/working/19_norm_pos.py")
RUN = f"python {PKG}/code/scripts/19_norm_pos.py --data-root {PKG}/tasks"
print(json.load(open(metas[0]))["script_sha256"])
"""),
        md("""
## 3. Smoke test (about 1 minute; dev split only, writes nothing)

The last lines must show `"device": "cuda"` and accuracies roughly 0.5 to 0.6. If this cell
fails, copy the error and stop.
"""),
        code("""
!{RUN} --smoke --systems word --normalizers none keyboard --jobs 2 --threads 1
"""),
        md("""
## 4. Full runs (36 runs; estimate under an hour on a T4, not measured)

Best started with **Save Version → Save & Run All (Commit)** so it keeps running with the
browser closed. Each finished run prints one line.
"""),
        code("""
!{RUN} --datasets sipos ud_sd --jobs 3 --threads 1 --out /kaggle/working
"""),
        md(
            "## 5. Quick look (the preregistered analysis is done locally with `scripts/20_norm_pos_report.py`)"
        ),
        code("""
import pandas as pd
for ds in ("sipos", "ud_sd"):
    f = f"/kaggle/working/runs_{ds}.jsonl"
    if os.path.exists(f):
        df = pd.read_json(f, lines=True)
        print("\\n==", ds, "| runs:", len(df))
        print(df.groupby(["system", "normalizer"])[["acc_clean", "acc_keyboard", "acc_kbnoise", "restored_pert"]].mean().round(4).to_string())
"""),
    ]
    nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                        "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}  # fmt: skip
    p = a.out / "morphtok_normpos_kaggle.ipynb"
    p.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
