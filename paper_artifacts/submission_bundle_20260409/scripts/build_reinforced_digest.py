#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from openfedbot.common import ensure_dir, load_json, save_json, timestamp_utc
from openfedbot.reporting import aggregate_rows, plot_operating_frontier, write_rows_csv
from openfedbot.statistics import HIGHER_IS_BETTER, hierarchical_paired_bootstrap_ci, metric_benefit, sign_test_pvalue


PAIRWISE_METRICS = [
    "unknown_misroute_rate",
    "accepted_benign_fpr",
    "selective_risk",
    "coverage",
    "accepted_known_macro_f1",
    "aurc",
]

SUMMARY_METRICS = [
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

DEPLOYMENT_METRICS = [
    "target_test_nodes",
    "target_unknown_nodes",
    "target_benign_nodes",
    "calibration_size",
    "multi_proto_count",
    "model_size_mb",
    "total_comm_mb",
    "total_runtime_sec",
    "target_inference_total_time_sec",
    "target_infer_sec_per_1k_targets",
    "end_to_end_sec_per_1k_targets",
    "end_to_end_nodes_per_sec",
    "auto_nodes_per_sec",
    "actionable_nodes_per_sec",
    "num_auto",
    "num_review",
    "num_final_defer",
    "review_queue_per_1k_targets",
    "defer_queue_per_1k_targets",
    "review_unknown_nodes",
    "review_benign_nodes",
    "auto_unknown_misroute_nodes",
]

RESOURCE_METRICS = [
    "train_time_sec",
    "source_infer_time_sec",
    "ova_fit_time_sec",
    "calibration_total_time_sec",
    "target_inference_total_time_sec",
    "evaluation_total_time_sec",
    "total_runtime_sec",
    "model_params",
    "model_size_mb",
    "active_clients",
    "rounds_completed",
    "uplink_mb",
    "downlink_mb",
    "total_comm_mb",
    "num_calibration_banks",
    "num_perturbations",
    "num_methods",
]

PAPER_MAIN_METHOD = "cpd_consensus"
PAPER_BASELINE_METHODS = ["ova_gate", "msp", "energy"]
PAPER_APPENDIX_METHODS = ["cpd_strict", "cpd_adapt", "cpd_adapt_consensus"]
PAPER_MAIN_POLICY = "triage_consensus_ova"
PAPER_APPENDIX_POLICIES = ["triage_strict_ova", "triage_adapt_consensus_ova"]
RELATION_ORDER = {"cross": 0, "same": 1}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build reinforced digest tables for OpenFedBot")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output-root", default=None)
    parser.add_argument("--reference-method", default="cpd_gate")
    parser.add_argument("--paper-main-method", default=None)
    parser.add_argument("--paper-baselines", nargs="+", default=None)
    parser.add_argument("--paper-main-policy", default=None)
    parser.add_argument("--paper-appendix-policies", nargs="+", default=None)
    parser.add_argument("--comparators", nargs="+", default=["msp", "energy"])
    parser.add_argument("--bank-selection", choices=["primary", "adaptive"], default="primary")
    parser.add_argument("--bank-selection-metric", default="cpd_val_coverage")
    parser.add_argument("--bank-selection-tie-break-metric", default="cpd_val_risk")
    parser.add_argument("--bootstrap-iters", type=int, default=10000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260403)
    parser.add_argument("--tie-tolerance", type=float, default=1e-4)
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_protocol_target_counts(run_dir: Path) -> dict[str, dict[str, float]]:
    counts: dict[str, dict[str, float]] = {}
    for path in sorted(run_dir.glob("*/protocol_summary.json")):
        payload = load_json(path)
        protocol_name = str(payload.get("protocol", path.parent.name))
        target_counts = dict(payload.get("target_counts", {}))
        counts[protocol_name] = {
            "target_test_nodes": float(target_counts.get("total_test_nodes", 0)),
            "target_known_nodes": float(target_counts.get("known_nodes", 0)),
            "target_unknown_nodes": float(target_counts.get("unknown_nodes", 0)),
            "target_benign_nodes": float(target_counts.get("benign_nodes", 0)),
            "target_known_bot_nodes": float(target_counts.get("known_bot_nodes", 0)),
            "num_classes": float(len(list(payload.get("class_names", [])))),
        }
    return counts


def annotate_relation(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in rows:
        item = dict(row)
        item["scenario_relation"] = "same" if item.get("source") == item.get("target") else "cross"
        out.append(item)
    return out


def primary_bank(rows: list[dict[str, str]]) -> str:
    if any(row.get("calibration_bank", "large") == "large" for row in rows):
        return "large"
    bank_fraction: dict[str, float] = {}
    for row in rows:
        name = row.get("calibration_bank", "large")
        fraction = float(row.get("calibration_fraction", "1.0"))
        bank_fraction[name] = max(bank_fraction.get(name, 0.0), fraction)
    if not bank_fraction:
        return "large"
    return max(bank_fraction.items(), key=lambda item: item[1])[0]


def is_clean_large(row: dict[str, str], primary_bank_name: str) -> bool:
    bank = row.get("calibration_bank", primary_bank_name)
    perturbation = row.get("perturbation", "clean")
    return bank == primary_bank_name and perturbation == "clean"


def is_clean(row: dict[str, str]) -> bool:
    return str(row.get("perturbation", "clean")) == "clean"


def select_banks_from_calibration(
    *,
    calibration_rows: list[dict[str, str]],
    selection_metric: str,
    tie_break_metric: str,
) -> list[dict[str, object]]:
    selected: dict[tuple[str, int], tuple[tuple[float, float], dict[str, str]]] = {}
    for row in calibration_rows:
        key = (str(row["protocol"]), int(row["seed"]))
        candidate = (float(row[str(selection_metric)]), -float(row[str(tie_break_metric)]))
        if key not in selected or candidate > selected[key][0]:
            selected[key] = (candidate, row)
    out: list[dict[str, object]] = []
    for (protocol, seed), (candidate, row) in sorted(selected.items()):
        out.append(
            {
                "protocol": protocol,
                "seed": int(seed),
                "source": row.get("source", ""),
                "target": row.get("target", ""),
                "holdout_family": row.get("holdout_family", ""),
                "selected_bank": str(row["calibration_bank"]),
                "selection_metric": str(selection_metric),
                "selection_metric_value": float(candidate[0]),
                "tie_break_metric": str(tie_break_metric),
                "tie_break_metric_value": float(-candidate[1]),
            }
        )
    return out


def select_rows_by_bank_assignments(
    *,
    rows: list[dict[str, str]],
    assignments: list[dict[str, object]],
    key_field: str,
) -> list[dict[str, str]]:
    assignment_map = {
        (str(item["protocol"]), int(item["seed"])): str(item[key_field])
        for item in assignments
    }
    out: list[dict[str, str]] = []
    for row in rows:
        key = (str(row["protocol"]), int(row["seed"]))
        if key not in assignment_map:
            continue
        if not is_clean(row):
            continue
        if str(row["calibration_bank"]) != assignment_map[key]:
            continue
        out.append(row)
    return out


def safe_ratio(num: float, den: float) -> float:
    return float(num / den) if float(den) > 0.0 else 0.0


def sort_grouped_rows(rows: list[dict[str, object]], *, key_name: str, order: list[str]) -> list[dict[str, object]]:
    rank: dict[str, int] = {}
    for name in order:
        if name not in rank:
            rank[name] = len(rank)
    return sorted(
        rows,
        key=lambda row: (
            RELATION_ORDER.get(str(row.get("scenario_relation", "")), 99),
            rank.get(str(row.get(key_name, "")), len(rank)),
            str(row.get(key_name, "")),
        ),
    )


def build_review_load_rows(triage_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in triage_rows:
        actionable = float(row["actionable_coverage"])
        auto = float(row["auto_coverage"])
        review_benign_rate = float(row["review_benign_rate"])
        review_unknown_capture = float(row["review_unknown_capture_rate"])
        action_gain = actionable - auto
        rows.append(
            {
                "scenario_relation": row["scenario_relation"],
                "policy": row["policy"],
                "auto_method": row["auto_method"],
                "review_method": row["review_method"],
                "protocol": row["protocol"],
                "seed": int(row["seed"]),
                "action_gain_over_auto": action_gain,
                "review_benign_rate": review_benign_rate,
                "review_benign_per_10k": 10000.0 * review_benign_rate,
                "review_unknown_capture_rate": review_unknown_capture,
                "review_unknown_capture_per_action_gain": safe_ratio(review_unknown_capture, action_gain),
                "review_benign_per_action_gain": safe_ratio(review_benign_rate, action_gain),
                "safe_unknown_handling_rate": float(row["safe_unknown_handling_rate"]),
                "safe_unknown_gap": 1.0 - float(row["safe_unknown_handling_rate"]),
                "final_defer_rate": float(row["final_defer_rate"]),
            }
        )
    return rows


def build_deployment_rows(
    *,
    triage_rows: list[dict[str, str]],
    resource_rows: list[dict[str, str]],
    calibration_rows: list[dict[str, str]],
    protocol_target_counts: dict[str, dict[str, float]],
) -> list[dict[str, object]]:
    resource_by_seed = {
        (str(row["protocol"]), int(row["seed"])): row
        for row in resource_rows
    }
    calibration_by_seed_bank = {
        (str(row["protocol"]), int(row["seed"]), str(row["calibration_bank"])): row
        for row in calibration_rows
        if is_clean(row)
    }

    rows: list[dict[str, object]] = []
    for row in triage_rows:
        protocol = str(row["protocol"])
        seed = int(row["seed"])
        resource = resource_by_seed.get((protocol, seed))
        calibration = calibration_by_seed_bank.get((protocol, seed, str(row["calibration_bank"])))
        target_counts = protocol_target_counts.get(protocol, {})

        target_test_nodes = float(row.get("num_samples", target_counts.get("target_test_nodes", 0.0)))
        target_unknown_nodes = float(target_counts.get("target_unknown_nodes", 0.0))
        target_benign_nodes = float(target_counts.get("target_benign_nodes", 0.0))
        num_auto = float(row.get("num_auto", 0.0))
        num_review = float(row.get("num_review", 0.0))
        num_final_defer = float(row.get("num_final_defer", 0.0))
        total_runtime_sec = float(resource["total_runtime_sec"]) if resource is not None else 0.0
        target_inference_total_time_sec = (
            float(resource["target_inference_total_time_sec"]) if resource is not None else 0.0
        )
        actionable_nodes = num_auto + num_review

        rows.append(
            {
                "scenario_relation": row["scenario_relation"],
                "policy": row["policy"],
                "auto_method": row["auto_method"],
                "review_method": row["review_method"],
                "protocol": protocol,
                "source": row["source"],
                "target": row["target"],
                "holdout_family": row["holdout_family"],
                "seed": seed,
                "calibration_bank": row["calibration_bank"],
                "calibration_fraction": float(row["calibration_fraction"]),
                "target_test_nodes": target_test_nodes,
                "target_unknown_nodes": target_unknown_nodes,
                "target_benign_nodes": target_benign_nodes,
                "calibration_size": float(row.get("calibration_size", 0.0)),
                "multi_proto_count": float(calibration.get("multi_proto_count", 0.0)) if calibration is not None else 0.0,
                "model_size_mb": float(resource["model_size_mb"]) if resource is not None else 0.0,
                "total_comm_mb": float(resource["total_comm_mb"]) if resource is not None else 0.0,
                "total_runtime_sec": total_runtime_sec,
                "target_inference_total_time_sec": target_inference_total_time_sec,
                "target_infer_sec_per_1k_targets": 1000.0 * safe_ratio(target_inference_total_time_sec, target_test_nodes),
                "end_to_end_sec_per_1k_targets": 1000.0 * safe_ratio(total_runtime_sec, target_test_nodes),
                "end_to_end_nodes_per_sec": safe_ratio(target_test_nodes, total_runtime_sec),
                "auto_nodes_per_sec": safe_ratio(num_auto, total_runtime_sec),
                "actionable_nodes_per_sec": safe_ratio(actionable_nodes, total_runtime_sec),
                "num_auto": num_auto,
                "num_review": num_review,
                "num_final_defer": num_final_defer,
                "review_queue_per_1k_targets": 1000.0 * safe_ratio(num_review, target_test_nodes),
                "defer_queue_per_1k_targets": 1000.0 * safe_ratio(num_final_defer, target_test_nodes),
                "review_unknown_nodes": float(row["review_unknown_capture_rate"]) * target_unknown_nodes,
                "review_benign_nodes": float(row["review_benign_rate"]) * target_benign_nodes,
                "auto_unknown_misroute_nodes": float(row["auto_unknown_misroute_rate"]) * target_unknown_nodes,
            }
        )
    return rows


def build_frontier_rows(
    *,
    clean_large_summary: list[dict[str, object]],
    triage_summary: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    auto_order = [PAPER_MAIN_METHOD, *PAPER_BASELINE_METHODS, *PAPER_APPENDIX_METHODS]
    triage_order = [PAPER_MAIN_POLICY, *PAPER_APPENDIX_POLICIES]
    for row in clean_large_summary:
        method = str(row["method"])
        if method not in auto_order:
            continue
        rows.append(
            {
                "scenario_relation": row["scenario_relation"],
                "label": method,
                "category": "auto",
                "operating_coverage": float(row["coverage_mean"]),
                "safe_unknown_handling": float(row["unknown_to_defer_rate_mean"]),
                "benign_cost_rate": float(row["accepted_benign_fpr_mean"]),
                "safety_gap": float(row["unknown_misroute_rate_mean"]),
            }
        )
    for row in triage_summary:
        policy = str(row["policy"])
        if policy not in triage_order:
            continue
        rows.append(
            {
                "scenario_relation": row["scenario_relation"],
                "label": policy,
                "category": "triage",
                "operating_coverage": float(row["actionable_coverage_mean"]),
                "safe_unknown_handling": float(row["safe_unknown_handling_rate_mean"]),
                "benign_cost_rate": float(row["review_benign_rate_mean"]),
                "safety_gap": 1.0 - float(row["safe_unknown_handling_rate_mean"]),
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            RELATION_ORDER.get(str(row["scenario_relation"]), 99),
            0 if str(row["category"]) == "auto" else 1,
            str(row["label"]),
        ),
    )


def rank_protocol_rows(
    rows: list[dict[str, object]],
    *,
    primary_metric: str,
    descending: bool = True,
) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(str(row["scenario_relation"]), []).append(row)

    ranked: list[dict[str, object]] = []
    for relation, relation_rows in grouped.items():
        ordered = sorted(
            relation_rows,
            key=lambda row: (
                -float(row[primary_metric]) if descending else float(row[primary_metric]),
                -float(row.get("unknown_misroute_rate_mean", row.get("auto_unknown_misroute_rate_mean", 0.0))),
                float(row.get("coverage_mean", row.get("actionable_coverage_mean", 0.0))),
                str(row["protocol"]),
            ),
        )
        for idx, row in enumerate(ordered, start=1):
            item = dict(row)
            item["rank_within_relation"] = idx
            ranked.append(item)
    return sorted(ranked, key=lambda row: (RELATION_ORDER.get(str(row["scenario_relation"]), 99), int(row["rank_within_relation"])))


def summarize_pairwise(
    rows: list[dict[str, str]],
    *,
    reference_method: str,
    comparator_method: str,
    metrics: list[str],
    tie_tolerance: float,
    bootstrap_iters: int,
    bootstrap_seed: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    indexed: dict[tuple[str, int, str], dict[str, str]] = {}
    for row in rows:
        indexed[(str(row["protocol"]), int(row["seed"]), str(row["method"]))] = row

    protocols = sorted({str(row["protocol"]) for row in rows})
    protocol_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    for metric in metrics:
        diffs_by_protocol: dict[str, np.ndarray] = {}
        reference_protocol_means: list[float] = []
        comparator_protocol_means: list[float] = []
        for protocol in protocols:
            seed_values: list[float] = []
            ref_values: list[float] = []
            cmp_values: list[float] = []
            meta_row = None
            for seed in sorted({int(row["seed"]) for row in rows if str(row["protocol"]) == protocol}):
                ref_row = indexed.get((protocol, seed, reference_method))
                cmp_row = indexed.get((protocol, seed, comparator_method))
                if ref_row is None or cmp_row is None:
                    continue
                ref_value = float(ref_row[metric])
                cmp_value = float(cmp_row[metric])
                seed_values.append(metric_benefit(ref_value, cmp_value, metric))
                ref_values.append(ref_value)
                cmp_values.append(cmp_value)
                meta_row = ref_row
            if not seed_values or meta_row is None:
                continue
            benefit = float(np.mean(seed_values))
            if benefit > float(tie_tolerance):
                outcome = "win"
            elif benefit < -float(tie_tolerance):
                outcome = "loss"
            else:
                outcome = "tie"
            diffs_by_protocol[protocol] = np.asarray(seed_values, dtype=np.float64)
            reference_protocol_means.append(float(np.mean(ref_values)))
            comparator_protocol_means.append(float(np.mean(cmp_values)))
            protocol_rows.append(
                {
                    "reference_method": reference_method,
                    "comparator_method": comparator_method,
                    "metric": metric,
                    "protocol": protocol,
                    "source": meta_row.get("source", ""),
                    "target": meta_row.get("target", ""),
                    "holdout_family": meta_row.get("holdout_family", ""),
                    "scenario_relation": "same" if meta_row.get("source") == meta_row.get("target") else "cross",
                    "reference_protocol_mean": float(np.mean(ref_values)),
                    "comparator_protocol_mean": float(np.mean(cmp_values)),
                    "benefit_for_reference": benefit,
                    "outcome": outcome,
                    "paired_seeds": len(seed_values),
                }
            )

        wins = int(sum(1 for row in protocol_rows if row["metric"] == metric and row["reference_method"] == reference_method and row["comparator_method"] == comparator_method and row["outcome"] == "win"))
        ties = int(sum(1 for row in protocol_rows if row["metric"] == metric and row["reference_method"] == reference_method and row["comparator_method"] == comparator_method and row["outcome"] == "tie"))
        losses = int(sum(1 for row in protocol_rows if row["metric"] == metric and row["reference_method"] == reference_method and row["comparator_method"] == comparator_method and row["outcome"] == "loss"))
        point_estimate, ci_low, ci_high = hierarchical_paired_bootstrap_ci(
            diffs_by_protocol,
            num_bootstrap=bootstrap_iters,
            seed=bootstrap_seed + len(summary_rows),
        )
        summary_rows.append(
            {
                "reference_method": reference_method,
                "comparator_method": comparator_method,
                "metric": metric,
                "direction": "higher_is_better" if metric in HIGHER_IS_BETTER else "lower_is_better",
                "reference_avg_across_protocols": float(np.mean(reference_protocol_means)) if reference_protocol_means else 0.0,
                "comparator_avg_across_protocols": float(np.mean(comparator_protocol_means)) if comparator_protocol_means else 0.0,
                "mean_protocol_benefit_for_reference": point_estimate,
                "bootstrap_ci_low": ci_low,
                "bootstrap_ci_high": ci_high,
                "wins": wins,
                "ties": ties,
                "losses": losses,
                "sign_test_pvalue": sign_test_pvalue(wins, losses),
                "protocol_count": len(diffs_by_protocol),
                "paired_seed_observations": int(sum(len(values) for values in diffs_by_protocol.values())),
            }
        )
    return protocol_rows, summary_rows


def main() -> None:
    global PAPER_MAIN_METHOD, PAPER_BASELINE_METHODS, PAPER_MAIN_POLICY, PAPER_APPENDIX_POLICIES
    args = parse_args()
    if args.paper_main_method:
        PAPER_MAIN_METHOD = str(args.paper_main_method)
    else:
        PAPER_MAIN_METHOD = str(args.reference_method)
    if args.paper_baselines:
        PAPER_BASELINE_METHODS = [str(item) for item in list(args.paper_baselines)]
    if args.paper_main_policy:
        PAPER_MAIN_POLICY = str(args.paper_main_policy)
    if args.paper_appendix_policies:
        PAPER_APPENDIX_POLICIES = [str(item) for item in list(args.paper_appendix_policies)]
    run_dir = Path(args.run_dir).expanduser().resolve()
    if args.output_root:
        output_root = Path(args.output_root).expanduser().resolve()
    else:
        output_root = run_dir.parent
    digest_dir = ensure_dir(output_root / f"reinforced_digest_{timestamp_utc()}")
    protocol_target_counts = load_protocol_target_counts(run_dir)

    calibration_rows = annotate_relation(read_rows(run_dir / "calibration_metrics.csv"))
    metric_rows = annotate_relation(read_rows(run_dir / "all_seed_metrics.csv"))
    resource_rows = annotate_relation(read_rows(run_dir / "resource_metrics.csv"))
    triage_rows = annotate_relation(read_rows(run_dir / "triage_seed_metrics.csv"))
    primary_bank_name = primary_bank(metric_rows)
    clean_large_rows = [row for row in metric_rows if is_clean_large(row, primary_bank_name)]
    triage_clean_primary = [row for row in triage_rows if is_clean_large(row, primary_bank_name)]

    selected_bank_assignments: list[dict[str, object]] = []
    paper_eval_rows = list(clean_large_rows)
    paper_triage_rows = list(triage_clean_primary)
    if str(args.bank_selection) == "adaptive":
        selected_bank_assignments = select_banks_from_calibration(
            calibration_rows=calibration_rows,
            selection_metric=str(args.bank_selection_metric),
            tie_break_metric=str(args.bank_selection_tie_break_metric),
        )
        paper_eval_rows = select_rows_by_bank_assignments(
            rows=metric_rows,
            assignments=selected_bank_assignments,
            key_field="selected_bank",
        )
        paper_triage_rows = select_rows_by_bank_assignments(
            rows=triage_rows,
            assignments=selected_bank_assignments,
            key_field="selected_bank",
        )
        write_rows_csv(digest_dir / "selected_bank_assignments.csv", selected_bank_assignments)
        write_rows_csv(digest_dir / "adaptive_bank_seed_metrics.csv", paper_eval_rows)
        write_rows_csv(digest_dir / "adaptive_bank_triage_seed_metrics.csv", paper_triage_rows)

    clean_large_summary = aggregate_rows(
        clean_large_rows,
        group_keys=["scenario_relation", "method"],
        metric_keys=SUMMARY_METRICS,
    )
    clean_large_summary = sort_grouped_rows(
        clean_large_summary,
        key_name="method",
        order=[PAPER_MAIN_METHOD, *PAPER_BASELINE_METHODS, *PAPER_APPENDIX_METHODS, args.reference_method],
    )
    write_rows_csv(digest_dir / "clean_large_method_summary.csv", clean_large_summary)

    for comparator in list(args.comparators):
        protocol_rows, summary_rows = summarize_pairwise(
            clean_large_rows,
            reference_method=str(args.reference_method),
            comparator_method=str(comparator),
            metrics=PAIRWISE_METRICS,
            tie_tolerance=float(args.tie_tolerance),
            bootstrap_iters=int(args.bootstrap_iters),
            bootstrap_seed=int(args.bootstrap_seed),
        )
        write_rows_csv(digest_dir / f"paired_{args.reference_method}_vs_{comparator}_protocol.csv", protocol_rows)
        write_rows_csv(digest_dir / f"paired_{args.reference_method}_vs_{comparator}_summary.csv", summary_rows)

    paper_method_summary_source = clean_large_summary
    if str(args.bank_selection) == "adaptive":
        paper_method_summary_source = aggregate_rows(
            paper_eval_rows,
            group_keys=["scenario_relation", "method"],
            metric_keys=SUMMARY_METRICS,
        )
        paper_method_summary_source = sort_grouped_rows(
            paper_method_summary_source,
            key_name="method",
            order=[PAPER_MAIN_METHOD, *PAPER_BASELINE_METHODS, *PAPER_APPENDIX_METHODS, args.reference_method],
        )
        write_rows_csv(digest_dir / "adaptive_bank_method_summary.csv", paper_method_summary_source)

        for comparator in list(args.comparators):
            protocol_rows, summary_rows = summarize_pairwise(
                paper_eval_rows,
                reference_method=str(args.reference_method),
                comparator_method=str(comparator),
                metrics=PAIRWISE_METRICS,
                tie_tolerance=float(args.tie_tolerance),
                bootstrap_iters=int(args.bootstrap_iters),
                bootstrap_seed=int(args.bootstrap_seed),
            )
            write_rows_csv(digest_dir / f"adaptive_paired_{args.reference_method}_vs_{comparator}_protocol.csv", protocol_rows)
            write_rows_csv(digest_dir / f"adaptive_paired_{args.reference_method}_vs_{comparator}_summary.csv", summary_rows)

    if any(row.get("perturbation", "clean") != "clean" for row in metric_rows):
        stress_rows = [row for row in metric_rows if row.get("calibration_bank", primary_bank_name) == primary_bank_name]
        stress_summary = aggregate_rows(
            stress_rows,
            group_keys=["scenario_relation", "perturbation", "perturbation_type", "perturbation_rate", "method"],
            metric_keys=SUMMARY_METRICS,
        )
        write_rows_csv(digest_dir / "stress_large_bank_summary.csv", stress_summary)

        cpd_stress_rows = [
            row
            for row in stress_rows
            if row["method"] == PAPER_MAIN_METHOD
        ]
        indexed_clean = {
            (row["protocol"], int(row["seed"]), row["scenario_relation"]): row
            for row in cpd_stress_rows
            if row.get("perturbation", "clean") == "clean"
        }
        delta_rows: list[dict[str, object]] = []
        for row in cpd_stress_rows:
            if row.get("perturbation", "clean") == "clean":
                continue
            clean_row = indexed_clean.get((row["protocol"], int(row["seed"]), row["scenario_relation"]))
            if clean_row is None:
                continue
            out = {
                "protocol": row["protocol"],
                "seed": int(row["seed"]),
                "scenario_relation": row["scenario_relation"],
                "perturbation": row["perturbation"],
                "perturbation_type": row.get("perturbation_type", ""),
                "perturbation_rate": float(row.get("perturbation_rate", "0")),
            }
            for metric in SUMMARY_METRICS:
                out[f"{metric}_delta_vs_clean"] = float(row[metric]) - float(clean_row[metric])
            delta_rows.append(out)
        write_rows_csv(digest_dir / "stress_cpd_delta_vs_clean.csv", delta_rows)
        if delta_rows:
            delta_summary = aggregate_rows(
                delta_rows,
                group_keys=["scenario_relation", "perturbation", "perturbation_type", "perturbation_rate"],
                metric_keys=[f"{metric}_delta_vs_clean" for metric in SUMMARY_METRICS],
            )
            write_rows_csv(digest_dir / "stress_cpd_delta_summary.csv", delta_summary)

    if any(row.get("calibration_bank", primary_bank_name) != primary_bank_name for row in metric_rows):
        bank_summary = aggregate_rows(
            [row for row in metric_rows if row.get("perturbation", "clean") == "clean"],
            group_keys=["scenario_relation", "calibration_bank", "calibration_fraction", "method"],
            metric_keys=SUMMARY_METRICS,
        )
        write_rows_csv(digest_dir / "calibration_bank_clean_summary.csv", bank_summary)

        cpd_bank_summary = aggregate_rows(
            [
                row
                for row in metric_rows
                if row.get("perturbation", "clean") == "clean" and row["method"] == PAPER_MAIN_METHOD
            ],
            group_keys=["scenario_relation", "calibration_bank", "calibration_fraction"],
            metric_keys=SUMMARY_METRICS,
        )
        write_rows_csv(digest_dir / "calibration_bank_cpd_summary.csv", cpd_bank_summary)

    runtime_overall: list[dict[str, object]] = []
    if resource_rows:
        runtime_protocol = aggregate_rows(
            resource_rows,
            group_keys=["protocol", "source", "target", "holdout_family", "scenario_relation"],
            metric_keys=RESOURCE_METRICS,
        )
        runtime_overall = aggregate_rows(
            resource_rows,
            group_keys=["scenario_relation"],
            metric_keys=RESOURCE_METRICS,
        )
        write_rows_csv(digest_dir / "runtime_comm_by_protocol.csv", runtime_protocol)
        write_rows_csv(digest_dir / "runtime_comm_overall.csv", runtime_overall)

    triage_summary: list[dict[str, object]] = []
    triage_clean: list[dict[str, str]] = []
    if triage_rows:
        triage_clean = triage_clean_primary
        triage_summary = aggregate_rows(
            triage_clean,
            group_keys=["scenario_relation", "policy", "auto_method", "review_method"],
            metric_keys=TRIAGE_METRICS,
        )
        triage_summary = sort_grouped_rows(
            triage_summary,
            key_name="policy",
            order=[PAPER_MAIN_POLICY, *PAPER_APPENDIX_POLICIES],
        )
        write_rows_csv(digest_dir / "triage_clean_summary.csv", triage_summary)

    paper_triage_summary_source = triage_summary
    paper_review_load_source_rows = triage_clean
    if str(args.bank_selection) == "adaptive":
        paper_triage_summary_source = aggregate_rows(
            paper_triage_rows,
            group_keys=["scenario_relation", "policy", "auto_method", "review_method"],
            metric_keys=TRIAGE_METRICS,
        )
        paper_triage_summary_source = sort_grouped_rows(
            paper_triage_summary_source,
            key_name="policy",
            order=[PAPER_MAIN_POLICY, *PAPER_APPENDIX_POLICIES],
        )
        paper_review_load_source_rows = paper_triage_rows
        write_rows_csv(digest_dir / "adaptive_bank_triage_summary.csv", paper_triage_summary_source)

    paper_main_method_summary = [
        row for row in paper_method_summary_source if str(row["method"]) in [PAPER_MAIN_METHOD, *PAPER_BASELINE_METHODS]
    ]
    paper_appendix_method_summary = [
        row for row in paper_method_summary_source if str(row["method"]) in PAPER_APPENDIX_METHODS
    ]
    write_rows_csv(digest_dir / "paper_main_method_summary.csv", paper_main_method_summary)
    write_rows_csv(digest_dir / "paper_appendix_method_summary.csv", paper_appendix_method_summary)

    paper_main_triage_summary = [
        row for row in paper_triage_summary_source if str(row["policy"]) == PAPER_MAIN_POLICY
    ]
    paper_appendix_triage_summary = [
        row for row in paper_triage_summary_source if str(row["policy"]) in PAPER_APPENDIX_POLICIES
    ]
    write_rows_csv(digest_dir / "paper_main_triage_summary.csv", paper_main_triage_summary)
    write_rows_csv(digest_dir / "paper_appendix_triage_summary.csv", paper_appendix_triage_summary)

    if runtime_overall:
        write_rows_csv(digest_dir / "paper_runtime_summary.csv", runtime_overall)

    if paper_review_load_source_rows:
        review_load_rows = build_review_load_rows(paper_review_load_source_rows)
        write_rows_csv(digest_dir / "triage_review_load_seed_metrics.csv", review_load_rows)
        review_load_summary = aggregate_rows(
            review_load_rows,
            group_keys=["scenario_relation", "policy", "auto_method", "review_method"],
            metric_keys=[
                "action_gain_over_auto",
                "review_benign_rate",
                "review_benign_per_10k",
                "review_unknown_capture_rate",
                "review_unknown_capture_per_action_gain",
                "review_benign_per_action_gain",
                "safe_unknown_handling_rate",
                "safe_unknown_gap",
                "final_defer_rate",
            ],
        )
        review_load_summary = sort_grouped_rows(
            review_load_summary,
            key_name="policy",
            order=[PAPER_MAIN_POLICY, *PAPER_APPENDIX_POLICIES],
        )
        write_rows_csv(digest_dir / "triage_review_load_summary.csv", review_load_summary)
        paper_review_load_summary = [
            row for row in review_load_summary if str(row["policy"]) == PAPER_MAIN_POLICY
        ]
        write_rows_csv(digest_dir / "paper_review_load_summary.csv", paper_review_load_summary)

    if paper_review_load_source_rows and resource_rows:
        deployment_rows = build_deployment_rows(
            triage_rows=paper_review_load_source_rows,
            resource_rows=resource_rows,
            calibration_rows=calibration_rows,
            protocol_target_counts=protocol_target_counts,
        )
        write_rows_csv(digest_dir / "deployment_seed_metrics.csv", deployment_rows)
        deployment_summary = aggregate_rows(
            deployment_rows,
            group_keys=["scenario_relation", "policy", "auto_method", "review_method"],
            metric_keys=DEPLOYMENT_METRICS,
        )
        deployment_summary = sort_grouped_rows(
            deployment_summary,
            key_name="policy",
            order=[PAPER_MAIN_POLICY, *PAPER_APPENDIX_POLICIES],
        )
        write_rows_csv(digest_dir / "deployment_policy_summary.csv", deployment_summary)
        paper_deployment_summary = [
            row for row in deployment_summary if str(row["policy"]) == PAPER_MAIN_POLICY
        ]
        write_rows_csv(digest_dir / "paper_deployment_summary.csv", paper_deployment_summary)

        paper_deployment_protocol_summary = aggregate_rows(
            [row for row in deployment_rows if str(row["policy"]) == PAPER_MAIN_POLICY],
            group_keys=["scenario_relation", "protocol", "source", "target", "holdout_family"],
            metric_keys=DEPLOYMENT_METRICS,
        )
        paper_deployment_protocol_summary = rank_protocol_rows(
            paper_deployment_protocol_summary,
            primary_metric="defer_queue_per_1k_targets_mean",
            descending=True,
        )
        write_rows_csv(digest_dir / "paper_deployment_protocol_summary.csv", paper_deployment_protocol_summary)

    if paper_triage_summary_source:
        frontier_rows = build_frontier_rows(
            clean_large_summary=paper_method_summary_source,
            triage_summary=paper_triage_summary_source,
        )
        write_rows_csv(digest_dir / "paper_operating_frontier.csv", frontier_rows)
        plot_operating_frontier(
            frontier_rows,
            digest_dir / "paper_operating_frontier.png",
            title="Safe Unknown Handling vs Coverage Frontier",
        )

        cpd_protocol_summary = aggregate_rows(
            [row for row in paper_eval_rows if str(row["method"]) == PAPER_MAIN_METHOD],
            group_keys=["scenario_relation", "protocol", "source", "target", "holdout_family"],
            metric_keys=SUMMARY_METRICS,
        )
        cpd_protocol_summary = rank_protocol_rows(
            cpd_protocol_summary,
            primary_metric="selective_risk_mean",
            descending=True,
        )
        write_rows_csv(digest_dir / "hardest_cpd_consensus_protocols.csv", cpd_protocol_summary)

        triage_protocol_summary = aggregate_rows(
            [row for row in paper_triage_rows if str(row["policy"]) == PAPER_MAIN_POLICY],
            group_keys=["scenario_relation", "protocol", "source", "target", "holdout_family"],
            metric_keys=TRIAGE_METRICS,
        )
        triage_protocol_summary = rank_protocol_rows(
            triage_protocol_summary,
            primary_metric="final_defer_rate_mean",
            descending=True,
        )
        write_rows_csv(digest_dir / "hardest_triage_consensus_ova_protocols.csv", triage_protocol_summary)

        hardest_cross_protocols = [
            str(row["protocol"])
            for row in cpd_protocol_summary
            if str(row["scenario_relation"]) == "cross" and int(row["rank_within_relation"]) <= 5
        ]
        hardest_comparison = aggregate_rows(
            [
                row
                for row in paper_eval_rows
                if str(row["protocol"]) in hardest_cross_protocols
                and str(row["method"]) in [PAPER_MAIN_METHOD, *PAPER_BASELINE_METHODS, *PAPER_APPENDIX_METHODS]
            ],
            group_keys=["scenario_relation", "protocol", "source", "target", "holdout_family", "method"],
            metric_keys=SUMMARY_METRICS,
        )
        hardest_comparison = sorted(
            hardest_comparison,
            key=lambda row: (
                RELATION_ORDER.get(str(row["scenario_relation"]), 99),
                hardest_cross_protocols.index(str(row["protocol"])) if str(row["protocol"]) in hardest_cross_protocols else 99,
                [PAPER_MAIN_METHOD, *PAPER_BASELINE_METHODS, *PAPER_APPENDIX_METHODS].index(str(row["method"])),
            ),
        )
        write_rows_csv(digest_dir / "hardest_protocol_method_comparison.csv", hardest_comparison)

    authoritative_outputs = {
        "main_method_summary": str(digest_dir / "paper_main_method_summary.csv"),
        "main_triage_summary": str(digest_dir / "paper_main_triage_summary.csv"),
        "review_load_summary": str(digest_dir / "paper_review_load_summary.csv"),
        "deployment_summary": str(digest_dir / "paper_deployment_summary.csv"),
        "deployment_protocol_summary": str(digest_dir / "paper_deployment_protocol_summary.csv"),
        "runtime_summary": str(digest_dir / "paper_runtime_summary.csv"),
        "frontier_csv": str(digest_dir / "paper_operating_frontier.csv"),
        "frontier_plot": str(digest_dir / "paper_operating_frontier.png"),
        "hardest_auto_protocols": str(digest_dir / "hardest_cpd_consensus_protocols.csv"),
        "hardest_triage_protocols": str(digest_dir / "hardest_triage_consensus_ova_protocols.csv"),
        "hardest_protocol_comparison": str(digest_dir / "hardest_protocol_method_comparison.csv"),
        "fixed_large_method_summary": str(digest_dir / "clean_large_method_summary.csv"),
        "all_policy_review_load_summary": str(digest_dir / "triage_review_load_summary.csv"),
        "selected_bank_assignments": str(digest_dir / "selected_bank_assignments.csv") if selected_bank_assignments else "",
    }
    if triage_rows:
        authoritative_outputs["fixed_large_triage_summary"] = str(digest_dir / "triage_clean_summary.csv")
    for comparator in list(args.comparators):
        paired_summary_path = digest_dir / f"paired_{args.reference_method}_vs_{comparator}_summary.csv"
        if paired_summary_path.exists():
            authoritative_outputs[f"paired_{args.reference_method}_vs_{comparator}_summary"] = str(paired_summary_path)
    if str(args.bank_selection) == "adaptive":
        authoritative_outputs["adaptive_method_summary"] = str(digest_dir / "adaptive_bank_method_summary.csv")
        authoritative_outputs["adaptive_triage_summary"] = str(digest_dir / "adaptive_bank_triage_summary.csv")
        for comparator in list(args.comparators):
            adaptive_summary_path = digest_dir / f"adaptive_paired_{args.reference_method}_vs_{comparator}_summary.csv"
            if adaptive_summary_path.exists():
                authoritative_outputs[f"adaptive_paired_{args.reference_method}_vs_{comparator}_summary"] = str(adaptive_summary_path)

    paper_manifest = {
        "paper_main_method": PAPER_MAIN_METHOD,
        "paper_main_policy": PAPER_MAIN_POLICY,
        "paper_baselines": PAPER_BASELINE_METHODS,
        "paper_appendix_methods": PAPER_APPENDIX_METHODS,
        "paper_appendix_policies": PAPER_APPENDIX_POLICIES,
        "bank_selection_mode": str(args.bank_selection),
        "bank_selection_metric": str(args.bank_selection_metric),
        "bank_selection_tie_break_metric": str(args.bank_selection_tie_break_metric),
        "authoritative_outputs": authoritative_outputs,
    }
    save_json(digest_dir / "paper_authoritative_manifest.json", paper_manifest)

    save_json(
        digest_dir / "manifest.json",
        {
            "run_dir": str(run_dir),
            "digest_dir": str(digest_dir),
            "reference_method": args.reference_method,
            "comparators": list(args.comparators),
            "primary_bank": primary_bank_name,
            "bank_selection_mode": str(args.bank_selection),
            "bank_selection_metric": str(args.bank_selection_metric),
            "bank_selection_tie_break_metric": str(args.bank_selection_tie_break_metric),
            "bootstrap_iters": int(args.bootstrap_iters),
            "tie_tolerance": float(args.tie_tolerance),
            "paper_main_method": PAPER_MAIN_METHOD,
            "paper_main_policy": PAPER_MAIN_POLICY,
        },
    )
    print(f"[OK] Reinforced digest created: {digest_dir}")


if __name__ == "__main__":
    main()
