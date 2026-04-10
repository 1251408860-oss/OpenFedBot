#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from openfedbot.common import ensure_dir, save_json, timestamp_utc
from openfedbot.reporting import aggregate_rows, write_rows_csv

AUTO_METRICS = [
    "coverage",
    "selective_risk",
    "accepted_benign_fpr",
    "accepted_known_bot_miss_rate",
    "unknown_to_defer_rate",
    "unknown_misroute_rate",
    "alerts_per_10k_benign",
    "accepted_known_macro_f1",
    "closed_known_macro_f1",
    "aurc",
]

TRIAGE_METRICS = [
    "auto_coverage",
    "review_coverage",
    "actionable_coverage",
    "final_defer_rate",
    "auto_selective_risk",
    "auto_unknown_misroute_rate",
    "review_unknown_capture_rate",
    "review_benign_rate",
    "safe_unknown_handling_rate",
    "review_known_macro_f1",
    "actionable_known_macro_f1",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize adaptive calibration-bank selection from an existing run")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output-root", default=None)
    parser.add_argument("--auto-method", default="cpd_consensus_plus")
    parser.add_argument("--triage-policy", default="triage_consensus_plus_prototype_or_ova_selective")
    parser.add_argument("--selection-metric", default="cpd_val_coverage")
    parser.add_argument("--tie-break-metric", default="cpd_val_risk")
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def clean_only(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not rows or "perturbation" not in rows[0]:
        return rows
    return [row for row in rows if str(row.get("perturbation", "clean")) == "clean"]


def with_relation(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for row in rows:
        item = dict(row)
        item["scenario_relation"] = "same" if item.get("source") == item.get("target") else "cross"
        out.append(item)
    return out


def main() -> None:
    args = parse_args()
    run_dir = Path(args.run_dir).expanduser().resolve()
    output_root = run_dir.parent if args.output_root is None else Path(args.output_root).expanduser().resolve()
    out_dir = ensure_dir(output_root / f"adaptive_bank_digest_{timestamp_utc()}")

    calibration_rows = read_rows(run_dir / "calibration_metrics.csv")
    metric_rows = clean_only(read_rows(run_dir / "all_seed_metrics.csv"))
    triage_rows = clean_only(read_rows(run_dir / "triage_seed_metrics.csv"))

    selected: dict[tuple[str, int], tuple[tuple[float, float], dict[str, str]]] = {}
    for row in calibration_rows:
        key = (str(row["protocol"]), int(row["seed"]))
        score = float(row[str(args.selection_metric)])
        tie_break = -float(row[str(args.tie_break_metric)])
        candidate = ((score, tie_break), row)
        if key not in selected or candidate[0] > selected[key][0]:
            selected[key] = candidate

    selection_rows: list[dict[str, object]] = []
    auto_selected_rows: list[dict[str, object]] = []
    triage_selected_rows: list[dict[str, object]] = []
    for (protocol, seed), (_, row) in sorted(selected.items()):
        bank = str(row["calibration_bank"])
        selection_rows.append(
            {
                "protocol": protocol,
                "seed": int(seed),
                "source": row.get("source", ""),
                "target": row.get("target", ""),
                "holdout_family": row.get("holdout_family", ""),
                "selected_bank": bank,
                "selection_metric": str(args.selection_metric),
                "selection_metric_value": float(row[str(args.selection_metric)]),
                "tie_break_metric": str(args.tie_break_metric),
                "tie_break_metric_value": float(row[str(args.tie_break_metric)]),
            }
        )
        auto_hits = [
            item
            for item in metric_rows
            if str(item["protocol"]) == protocol
            and int(item["seed"]) == int(seed)
            and str(item["calibration_bank"]) == bank
            and str(item["method"]) == str(args.auto_method)
        ]
        auto_selected_rows.extend(with_relation(auto_hits))
        triage_hits = [
            item
            for item in triage_rows
            if str(item["protocol"]) == protocol
            and int(item["seed"]) == int(seed)
            and str(item["calibration_bank"]) == bank
            and str(item["policy"]) == str(args.triage_policy)
        ]
        triage_selected_rows.extend(with_relation(triage_hits))

    auto_summary = aggregate_rows(
        auto_selected_rows,
        group_keys=["scenario_relation", "method"],
        metric_keys=AUTO_METRICS,
    )
    triage_summary = aggregate_rows(
        triage_selected_rows,
        group_keys=["scenario_relation", "policy", "auto_method", "review_method"],
        metric_keys=TRIAGE_METRICS,
    )

    hardest_cross = sorted(
        [row for row in auto_selected_rows if str(row["scenario_relation"]) == "cross"],
        key=lambda item: (-float(item["selective_risk"]), float(item["coverage"]), str(item["protocol"]), int(item["seed"])),
    )

    write_rows_csv(out_dir / "selected_bank_assignments.csv", selection_rows)
    write_rows_csv(out_dir / "auto_selected_seed_metrics.csv", auto_selected_rows)
    write_rows_csv(out_dir / "triage_selected_seed_metrics.csv", triage_selected_rows)
    write_rows_csv(out_dir / "adaptive_bank_auto_summary.csv", auto_summary)
    write_rows_csv(out_dir / "adaptive_bank_triage_summary.csv", triage_summary)
    write_rows_csv(out_dir / "adaptive_bank_hardest_cross_seed_metrics.csv", hardest_cross)
    save_json(
        out_dir / "manifest.json",
        {
            "run_dir": str(run_dir),
            "output_dir": str(out_dir),
            "auto_method": str(args.auto_method),
            "triage_policy": str(args.triage_policy),
            "selection_metric": str(args.selection_metric),
            "tie_break_metric": str(args.tie_break_metric),
        },
    )
    print(str(out_dir))


if __name__ == "__main__":
    main()
