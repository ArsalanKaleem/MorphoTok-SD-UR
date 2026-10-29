"""Gate 1: ZWNJ / format-character audit and annotation-sheet generation.

Outputs (under ``runs/<experiment_id>/``): audit JSON, a stratified annotation sheet,
and -- only if completed annotations exist -- the proportion of ZWNJ occurrences that
coincide with morphological boundaries (Wilson 95% CI) plus inter-annotator agreement.
On synthetic data the labels come from construction-time gold (an oracle), which
only exercises the code path.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audit.agreement import adjudicate, pairwise_report

from morphtok.data.loaders import DataUnavailableError, resolve
from morphtok.experiments.results import finalise, new_record
from morphtok.experiments.runner import (
    SYNTHETIC_BANNER,
    cli,
    exp_id,
    fmt,
    load_dataset,
    print_table,
)
from morphtok.unicode_audit.contexts import (
    extract_occurrences,
    load_annotations,
    morph_rate,
    oracle_labels_from_gold,
    stratified_sample,
    write_annotation_sheet,
)
from morphtok.unicode_audit.zwnj_stats import audit_lines, load_joining_types


def main() -> int:
    """Run the audit and print the Gate 1 report."""
    _, run, out = cli(__doc__ or "")
    try:
        ds = load_dataset(run)
    except DataUnavailableError as e:
        print(f"GATE 1 SKIPPED: {e}")
        return 2
    g1 = run.get("gate1", {})
    eid = exp_id("G1-zwnj-audit", ds)
    rec = new_record(eid, g1.get("sample_seed"), run, ds.describe(), ds.synthetic)
    if ds.synthetic:
        print(SYNTHETIC_BANNER)
    joining = load_joining_types(resolve(g1.get("arabic_shaping_path")))
    if joining is None:
        rec["warnings"].append("joining-class data unavailable (no ArabicShaping.txt configured)")
    audit = {form: audit_lines(ds.lines, form, joining) for form in ("NFC", "NFKC", "none")}
    rec["metrics"]["audit"] = audit
    nfc = audit["NFC"]
    print(f"\nLines {nfc['n_lines']}  words {nfc['n_words']}  chars {nfc['n_chars']}  "
          f"Unicode {nfc['unicode_version']}  joining data: {nfc['joining_data']}")  # fmt: skip
    for form in ("NFC", "NFKC"):
        print(f"lines changed by {form}: {audit[form]['n_lines_changed_by_normalization']}")
    rows = []
    for cp, st in nfc["format_chars"].items():
        pos = st["position"]
        rows.append([cp, str(st["count"]), str(st["words_containing"]),
                     str(pos.get("initial", 0)), str(pos.get("medial", 0)), str(pos.get("final", 0)),
                     str(pos.get("isolated", 0)), json.dumps(st["run_lengths"])])  # fmt: skip
    print("\nFormat characters (NFC):")
    print_table(
        ["codepoint", "count", "words", "initial", "medial", "final", "isolated", "run lengths"], rows
    )
    zw = nfc["format_chars"].get("U+200C")
    if zw:
        print("\nTop left-neighbour classes of ZWNJ:", zw["left_class"])
        print("Top right-neighbour classes of ZWNJ:", zw["right_class"])

    occs = extract_occurrences(ds.lines, "NFC", int(g1.get("context_window", 20)))
    sample = stratified_sample(occs, int(g1.get("sample_size", 200)), int(g1.get("sample_seed", 13)))
    sheet = out / eid / "zwnj_annotation_sheet.tsv"
    write_annotation_sheet(sample, sheet)
    print(f"\nZWNJ occurrences: {len(occs)}; stratified sample of {len(sample)} written to {sheet}")
    rec["metrics"]["n_occurrences"] = len(occs)
    rec["metrics"]["n_sampled"] = len(sample)

    ann_path = resolve(ds.cfg.zwnj_annotation_path)
    if ann_path is not None and ann_path.exists():
        ratings = load_annotations(ann_path)
        labels = adjudicate(ratings)
        rate = morph_rate(labels)
        rec["metrics"]["agreement"] = pairwise_report(ratings)
        source = "human annotations (adjudicated)"
    elif ds.synthetic:
        gold = {w: e.boundaries for w, e in ds.gold.items()}
        rate = morph_rate(oracle_labels_from_gold(sample, gold))
        source = "SYNTHETIC oracle labels from construction-time gold"
    else:
        rate = None
        source = "none"
        rec["skipped_steps"].append("MORPH-rate: no completed ZWNJ annotations")
    rec["metrics"]["morph_rate"] = rate
    rec["metrics"]["label_source"] = source
    print(f"\nLabel source: {source}")
    if rate is None:
        print("H2 (ZWNJ marks morphology in a minority of occurrences): UNRESOLVED -- annotate the sheet "
              "following audit/annotation_guidelines.md, then set zwnj_annotations.path.")  # fmt: skip
    else:
        ci = rate["wilson_95"]
        print(f"MORPH rate = {fmt(rate['morph_rate'])}  95% CI = "
              f"[{fmt(ci[0]) if ci else 'n/a'}, {fmt(ci[1]) if ci else 'n/a'}]  n = {rate['denominator']}")  # fmt: skip
        print("Gate 1 decision threshold: UNRESOLVED until the pilot (prereg/decision_gates.md).")
    path = finalise(rec, out)
    print(f"\nrecord: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
