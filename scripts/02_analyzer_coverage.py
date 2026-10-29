"""Gate 2: analyzer coverage, boundary precision/recall against gold, and calibration.

If no real analyzer is configured this script says so explicitly and records the
step as skipped; it never reports a null analyzer's zero coverage as a finding.
Precision/recall are computed on the **dev** gold types only.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from morphtok.analyzers.base import AnalyzerNotConfiguredError, coverage
from morphtok.analyzers.confidence import aggregate, calibration_table
from morphtok.data.loaders import DataUnavailableError
from morphtok.eval.morph_boundary import boundary_prf
from morphtok.experiments.results import finalise, new_record
from morphtok.experiments.runner import (
    SYNTHETIC_BANNER,
    build_analyzer,
    cli,
    exp_id,
    fmt,
    load_dataset,
    print_table,
    stripped_counts,
)


def main() -> int:
    """Report coverage and reliability for the configured analyzer (and perturbations)."""
    _, run, out = cli(__doc__ or "")
    try:
        ds = load_dataset(run)
    except DataUnavailableError as e:
        an_cfg = run["data_cfg"].get("analyzer", {}) or {}
        configured = bool(an_cfg.get("rules_path") or an_cfg.get("command"))
        print(f"Analyzer configured for {run['data_cfg']['name']!r}: "
              f"{'yes (unverified)' if configured else 'NO REAL ANALYZER CONFIGURED'} (type {an_cfg.get('type')!r})")  # fmt: skip
        print(f"GATE 2 SKIPPED: {e}")
        return 2
    if ds.synthetic:
        print(SYNTHETIC_BANNER)
    counts = stripped_counts(ds.splits["train"])
    gold_dev = ds.gold_for("dev")
    conditions = [{}]
    if ds.synthetic:
        conditions += run.get("ablations", {}).get("analyzer_perturbations", [])[1:]
    rows = []
    for cond in conditions:
        analyzer = build_analyzer(ds, cond)
        eid = exp_id(f"G2-coverage-{analyzer.name}", ds)
        rec = new_record(
            eid, cond.get("seed", 0), {"run": run, "condition": cond}, ds.describe(), ds.synthetic
        )
        rec["metrics"]["analyzer"] = {"name": analyzer.name, "version": analyzer.version, "condition": cond}
        if not analyzer.is_configured:
            msg = (f"NO REAL ANALYZER CONFIGURED for dataset {ds.cfg.name!r} (analyzer type "
                   f"{ds.cfg.analyzer.get('type')!r}). Coverage and precision are UNRESOLVED; H3 cannot be "
                   "tested. Configure a verified resource in configs/data/*.yaml.")  # fmt: skip
            print(msg)
            rec["skipped_steps"].append(msg)
            finalise(rec, out, "skipped")
            return 0
        try:
            rep = coverage(analyzer, counts.items())
            preds, golds, confs = [], [], {}
            for w in sorted(gold_dev):
                try:
                    analyses = analyzer.analyze(w)
                except AnalyzerNotConfiguredError:
                    analyses = []
                if not analyses:
                    continue
                c = aggregate(analyses)
                confs[w] = c
                preds.append({k for k, v in c.items() if v > 0})
                golds.append(set(gold_dev[w]))
            pr = boundary_prf(preds, golds)
            cal = calibration_table(confs, gold_dev, int(run.get("gate2", {}).get("calibration_bins", 10)))
        except Exception as e:
            finalise(rec, out, "failed", e)
            raise
        rec["metrics"].update({
            "type_coverage": rep.type_coverage, "token_coverage": rep.token_coverage,
            "n_types": rep.n_types, "error_types": rep.error_types, "ambiguous_types": rep.ambiguous_types,
            "boundary_vs_dev_gold_on_covered": pr, "n_dev_gold_covered": len(preds),
            "n_dev_gold": len(gold_dev), "calibration": cal,
        })  # fmt: skip
        finalise(rec, out)
        rows.append([analyzer.name, str(cond or "as configured"), fmt(rep.type_coverage), fmt(rep.token_coverage),
                     f"{len(preds)}/{len(gold_dev)}", fmt(pr["precision"]), fmt(pr["recall"]), fmt(pr["f1"]),
                     fmt(cal["ece"])])  # fmt: skip
    print("\nGate 2 -- analyzer coverage (train types/tokens) and reliability on covered dev gold types")
    print_table(
        ["analyzer", "condition", "type cov", "token cov", "dev covered", "P", "R", "F1", "ECE"], rows
    )
    print("\nGate 2 thresholds (minimum coverage / precision): UNRESOLVED until the pilot.")
    if ds.synthetic:
        print(
            "The synthetic oracle is gold by construction; its precision is uninformative about real analyzers."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
