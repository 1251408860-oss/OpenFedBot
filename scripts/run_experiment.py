#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path
from time import perf_counter

import numpy as np
import torch

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from openfedbot.calibration import (
    build_method_outputs,
    calibrate_ova_gate,
    fit_calibrator,
    fit_ova_model,
    fit_review_selector,
    subsample_calibration_bank,
)
from openfedbot.common import ensure_dir, load_json, save_json, timestamp_utc
from openfedbot.data import build_client_views, build_protocol_data, load_scenario_bundle, scenario_counts
from openfedbot.federated import adapt_with_target_confidence, finetune_group_dro, infer_logits_embeddings, run_fedavg_training
from openfedbot.metrics import evaluate_method, evaluate_triage_policy, risk_coverage_curve
from openfedbot.perturb import apply_graph_perturbation
from openfedbot.reporting import aggregate_rows, plot_risk_coverage, plot_unknown_routing, write_rows_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run OpenFedBot experiments")
    parser.add_argument("--config", required=True)
    return parser.parse_args()


def repo_path(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return (root / path).resolve()


def input_root(cfg: dict[str, object]) -> Path:
    if cfg.get("graph_root") is not None:
        return repo_path(PROJECT_ROOT, str(cfg["graph_root"]))
    if cfg.get("hitrust_root") is not None:
        return repo_path(PROJECT_ROOT, str(cfg["hitrust_root"]))
    return PROJECT_ROOT


def resolve_scenario_spec(
    *,
    root: Path,
    raw_value: object,
) -> tuple[Path, Path | None]:
    if isinstance(raw_value, str):
        return repo_path(root, raw_value), None

    item = dict(raw_value)
    graph_path = repo_path(root, str(item["graph_path"]))
    manifest_path = None
    if item.get("manifest_path") is not None:
        manifest_path = repo_path(root, str(item["manifest_path"]))
    return graph_path, manifest_path


def load_calibration_banks(cfg: dict[str, object]) -> list[dict[str, object]]:
    raw_banks = list(cfg.get("calibration_banks", [{"name": "large", "fraction": 1.0}]))
    banks: list[dict[str, object]] = []
    for item in raw_banks:
        bank = dict(item)
        banks.append(
            {
                "name": str(bank["name"]),
                "fraction": float(bank["fraction"]),
            }
        )
    return banks


def load_stress_tests(cfg: dict[str, object]) -> list[dict[str, object]]:
    raw_tests = list(cfg.get("stress_tests", [{"name": "clean", "type": "clean", "rate": 0.0}]))
    tests: list[dict[str, object]] = []
    for item in raw_tests:
        test = dict(item)
        tests.append(
            {
                "name": str(test["name"]),
                "type": str(test["type"]),
                "rate": float(test["rate"]),
            }
        )
    return tests


def stable_seed(base_seed: int, *parts: object) -> int:
    token = ":".join(str(part) for part in parts)
    checksum = sum((idx + 1) * ord(ch) for idx, ch in enumerate(token))
    return int(base_seed + 1009 * checksum)


def preferred_plot_bank(calibration_banks: list[dict[str, object]]) -> str:
    for bank in calibration_banks:
        if str(bank["name"]) == "large":
            return str(bank["name"])
    return str(max(calibration_banks, key=lambda item: float(item["fraction"]))["name"])


def target_pseudo_methods(cfg: dict[str, object]) -> list[str]:
    raw = cfg.get("target_pseudo_methods")
    if raw is None:
        return [str(cfg.get("target_pseudo_method", "cpd_consensus_plus"))]
    methods = [str(item) for item in list(raw)]
    if not methods:
        raise ValueError("target_pseudo_methods must not be empty")
    return methods


def build_group_dro_ids(
    *,
    protocol,
    cfg: dict[str, object],
) -> tuple[torch.Tensor, dict[str, object]]:
    group_key = str(cfg.get("group_dro_group_key", "family_time"))
    num_time_bins = max(int(cfg.get("group_dro_time_bins", 4)), 1)
    num_nodes = int(protocol.source.graph.num_nodes)
    window_idx = protocol.source.graph.window_idx.detach().cpu().numpy().astype(np.int64, copy=False)
    family_tokens = np.asarray(protocol.source.node_family, dtype=object)
    tokens = np.full((num_nodes,), "unknown", dtype=object)

    if group_key == "family":
        tokens = family_tokens.astype(object, copy=True)
    elif group_key == "time_bucket":
        valid = window_idx >= 0
        if int(valid.sum()) > 0:
            lo = int(window_idx[valid].min())
            hi = int(window_idx[valid].max())
            span = max(hi - lo + 1, 1)
            bucket = np.full((num_nodes,), -1, dtype=np.int64)
            bucket[valid] = np.minimum(((window_idx[valid] - lo) * num_time_bins) // span, num_time_bins - 1)
            tokens = np.asarray([f"time_{int(item)}" for item in bucket], dtype=object)
    elif group_key == "family_time":
        valid = window_idx >= 0
        lo = int(window_idx[valid].min()) if int(valid.sum()) > 0 else 0
        hi = int(window_idx[valid].max()) if int(valid.sum()) > 0 else 0
        span = max(hi - lo + 1, 1)
        bucket = np.full((num_nodes,), -1, dtype=np.int64)
        bucket[valid] = np.minimum(((window_idx[valid] - lo) * num_time_bins) // span, num_time_bins - 1)
        tokens = np.asarray(
            [f"{str(family_tokens[idx])}|time_{int(bucket[idx])}" for idx in range(num_nodes)],
            dtype=object,
        )
    else:
        raise KeyError(f"unknown group_dro_group_key: {group_key}")

    active_tokens = [str(tokens[idx]) for idx in np.flatnonzero(protocol.source_train_mask.detach().cpu().numpy())]
    unique_tokens = sorted(set(active_tokens))
    token_to_id = {token: idx for idx, token in enumerate(unique_tokens)}
    group_ids = torch.full((num_nodes,), -1, dtype=torch.long)
    for idx, token in enumerate(tokens.tolist()):
        if str(token) in token_to_id:
            group_ids[int(idx)] = int(token_to_id[str(token)])
    return group_ids, {
        "group_key": group_key,
        "time_bins": int(num_time_bins),
        "groups": unique_tokens,
    }


def _normalized_pseudo_weights(
    *,
    accept: np.ndarray,
    best_score: np.ndarray,
    min_weight: float,
) -> np.ndarray:
    weights = np.zeros_like(best_score, dtype=np.float64)
    accept_mask = np.asarray(accept, dtype=bool, copy=False)
    if int(accept_mask.sum()) <= 0:
        return weights
    active_scores = np.asarray(best_score[accept_mask], dtype=np.float64, copy=False)
    lo = float(np.quantile(active_scores, 0.1, method="lower"))
    hi = float(np.quantile(active_scores, 0.9, method="higher"))
    if hi <= lo + 1e-12:
        weights[accept_mask] = 1.0
        return weights
    scaled = (active_scores - lo) / max(hi - lo, 1e-6)
    scaled = np.clip(scaled, 0.0, 1.0)
    floor = min(max(float(min_weight), 0.0), 1.0)
    weights[accept_mask] = floor + (1.0 - floor) * scaled
    return weights


def _cap_pseudo_ratio(
    *,
    accept: np.ndarray,
    best_score: np.ndarray,
    max_ratio: float,
    total_count: int,
) -> np.ndarray:
    accept_mask = np.asarray(accept, dtype=bool, copy=False)
    cap = min(max(float(max_ratio), 0.0), 1.0)
    if cap <= 0.0 or int(accept_mask.sum()) <= 0:
        return np.zeros_like(accept_mask, dtype=bool)
    max_keep = int(np.floor(float(total_count) * cap))
    max_keep = max(max_keep, 1)
    if int(accept_mask.sum()) <= max_keep:
        return accept_mask.copy()
    accepted_idx = np.flatnonzero(accept_mask)
    accepted_scores = np.asarray(best_score[accepted_idx], dtype=np.float64, copy=False)
    order = np.argsort(-accepted_scores, kind="stable")
    keep_idx = accepted_idx[order[:max_keep]]
    capped = np.zeros_like(accept_mask, dtype=bool)
    capped[keep_idx] = True
    return capped


def _stage_scaled_ratio(
    *,
    base_ratio: float | None,
    stage_index: int,
    growth: float,
) -> float | None:
    if base_ratio is None:
        return None
    base = min(max(float(base_ratio), 0.0), 1.0)
    if base <= 0.0:
        return 0.0
    scale = max(float(growth), 1.0)
    return min(base * (scale ** max(int(stage_index), 0)), 1.0)


def main() -> None:
    args = parse_args()
    cfg = load_json(args.config)
    graph_root = input_root(cfg)
    output_root = repo_path(PROJECT_ROOT, str(cfg["output_root"]))
    run_name = str(cfg.get("run_name", "open_world_run"))
    run_dir = ensure_dir(output_root / f"{run_name}_{timestamp_utc()}")
    save_json(run_dir / "config.snapshot.json", cfg)

    scenarios = {}
    resolved_scenarios: dict[str, dict[str, str]] = {}
    for scenario_name, raw_spec in dict(cfg["scenario_graphs"]).items():
        graph_path, manifest_path = resolve_scenario_spec(
            root=graph_root,
            raw_value=raw_spec,
        )
        scenarios[str(scenario_name)] = load_scenario_bundle(
            str(scenario_name),
            graph_path,
            manifest_file=manifest_path,
        )
        resolved_scenarios[str(scenario_name)] = {
            "graph_path": str(graph_path),
            "manifest_path": str(manifest_path) if manifest_path is not None else "",
        }
    save_json(
        run_dir / "resolved_inputs.json",
        {
            "graph_root": str(graph_root),
            "scenario_graphs": resolved_scenarios,
        },
    )

    seeds = [int(seed) for seed in list(cfg["seeds"])]
    calibration_banks = load_calibration_banks(cfg)
    stress_tests = load_stress_tests(cfg)
    include_ova_gate = bool(cfg.get("include_ova_gate", False))
    metric_rows: list[dict[str, object]] = []
    triage_rows: list[dict[str, object]] = []
    resource_rows: list[dict[str, object]] = []
    calibration_rows: list[dict[str, object]] = []
    perturbation_rows: list[dict[str, object]] = []
    curve_cache: dict[str, dict[str, dict[str, np.ndarray]]] = {}
    protocol_summaries: list[dict[str, object]] = []
    plot_bank = preferred_plot_bank(calibration_banks)
    plot_perturbation = "clean"

    for protocol_cfg in list(cfg["protocols"]):
        protocol_name = str(protocol_cfg["name"])
        source_name = str(protocol_cfg["source"])
        target_name = str(protocol_cfg["target"])
        holdout_family = str(protocol_cfg["holdout_family"])
        target_mode = str(protocol_cfg["target_mode"])
        protocol = build_protocol_data(
            source=scenarios[source_name],
            target=scenarios[target_name],
            holdout_family=holdout_family,
            target_mode=target_mode,
        )
        protocol_dir = ensure_dir(run_dir / protocol_name)
        save_json(
            protocol_dir / "protocol_summary.json",
            {
                "protocol": protocol_name,
                "source": source_name,
                "target": target_name,
                "holdout_family": holdout_family,
                "class_names": protocol.class_names,
                "source_counts": scenario_counts(protocol.source, protocol.source_labels, protocol.source_test_mask),
                "target_counts": scenario_counts(protocol.target, protocol.target_labels, protocol.target_test_mask),
            },
        )
        curve_cache[protocol_name] = {}
        support_mask = protocol.target.graph.ip_idx < 0
        target_x = protocol.target.graph.x_norm.float()
        target_edge_index = protocol.target.graph.edge_index.long()
        test_labels = protocol.target_labels[protocol.target_test_mask].detach().cpu().numpy()
        protocol_resource_rows: list[dict[str, object]] = []
        protocol_triage_rows: list[dict[str, object]] = []
        protocol_calibration_rows: list[dict[str, object]] = []
        protocol_perturbation_rows: list[dict[str, object]] = []

        for seed in seeds:
            client_views = build_client_views(
                bundle=protocol.source,
                labels=protocol.source_labels,
                train_mask=protocol.source_train_mask,
                num_clients=int(cfg["num_clients"]),
                partition_mode=str(cfg["partition_mode"]),
                seed=seed,
            )
            train_start = perf_counter()
            model, training_summary = run_fedavg_training(
                source_graph=protocol.source.graph,
                source_labels=protocol.source_labels,
                train_mask=protocol.source_train_mask,
                val_mask=protocol.source_val_mask,
                client_views=client_views,
                num_classes=len(protocol.class_names),
                seed=seed,
                hidden_dim=int(cfg["hidden_dim"]),
                dropout=float(cfg.get("dropout", 0.2)),
                global_warmup_epochs=int(cfg["global_warmup_epochs"]),
                rounds=int(cfg["rounds"]),
                local_epochs=int(cfg["local_epochs"]),
                lr=float(cfg["lr"]),
                edge_dropout_prob=float(cfg.get("train_edge_dropout", 0.0)),
                center_loss_weight=float(cfg.get("center_loss_weight", 0.0)),
                center_margin_weight=float(cfg.get("center_margin_weight", 0.0)),
                center_margin_value=float(cfg.get("center_margin_value", 0.15)),
            )
            train_time_sec = float(perf_counter() - train_start)
            if bool(cfg.get("group_dro_finetune_enabled", False)):
                group_ids, group_dro_meta = build_group_dro_ids(protocol=protocol, cfg=cfg)
                group_dro_start = perf_counter()
                model, group_dro_summary = finetune_group_dro(
                    model,
                    x=protocol.source.graph.x_norm.float(),
                    edge_index=protocol.source.graph.edge_index.long(),
                    labels=protocol.source_labels,
                    mask=protocol.source_train_mask,
                    group_ids=group_ids,
                    epochs=int(cfg.get("group_dro_epochs", 0)),
                    lr=float(cfg.get("group_dro_lr", cfg["lr"])),
                    num_classes=len(protocol.class_names),
                    val_mask=protocol.source_val_mask,
                        group_dro_eta=float(cfg.get("group_dro_eta", 0.1)),
                        edge_dropout_prob=float(cfg.get("train_edge_dropout", 0.0)),
                        center_loss_weight=float(cfg.get("center_loss_weight", 0.0)),
                        center_margin_weight=float(cfg.get("center_margin_weight", 0.0)),
                        center_margin_value=float(cfg.get("center_margin_value", 0.15)),
                    )
                group_dro_summary.update(
                    {
                        "group_dro_time_sec": float(perf_counter() - group_dro_start),
                        **group_dro_meta,
                    }
                )
                training_summary["group_dro"] = group_dro_summary
                train_time_sec += float(group_dro_summary["group_dro_time_sec"])
            save_json(protocol_dir / f"training_seed_{seed}.json", training_summary)

            source_infer_start = perf_counter()
            src_logits, src_embeddings = infer_logits_embeddings(
                model,
                x=protocol.source.graph.x_norm.float(),
                edge_index=protocol.source.graph.edge_index.long(),
            )
            source_infer_time_sec = float(perf_counter() - source_infer_start)

            val_logits_full = src_logits[protocol.source_val_mask]
            val_embeddings_full = src_embeddings[protocol.source_val_mask]
            val_labels_full = protocol.source_labels[protocol.source_val_mask]
            train_embeddings = src_embeddings
            train_labels = protocol.source_labels
            train_mask = protocol.source_train_mask

            ova_model = None
            ova_fit_time_sec = 0.0
            if include_ova_gate:
                ova_fit_start = perf_counter()
                ova_model = fit_ova_model(
                    train_embeddings=train_embeddings,
                    train_labels=train_labels,
                    train_mask=train_mask,
                    num_classes=len(protocol.class_names),
                )
                ova_fit_time_sec = float(perf_counter() - ova_fit_start)

            if bool(cfg.get("target_confidence_adapt_enabled", False)) and ova_model is not None:
                stage_count = max(int(cfg.get("target_confidence_adapt_stages", 1)), 1)
                pseudo_ratio_growth = float(cfg.get("target_pseudo_ratio_growth", 1.0))
                flow_indices = torch.nonzero(protocol.target.flow_mask, as_tuple=False).view(-1)
                flow_count = int(protocol.target.flow_mask.sum().item())
                stage_summaries: list[dict[str, object]] = []
                for stage_idx in range(stage_count):
                    pre_adapt_gate = calibrate_ova_gate(
                        ova_model=ova_model,
                        val_embeddings=val_embeddings_full,
                        coverage_target=float(cfg["coverage_target"]),
                    )
                    pre_adapt_calibrator = fit_calibrator(
                        val_logits=val_logits_full,
                        val_embeddings=val_embeddings_full,
                        val_labels=val_labels_full,
                        train_embeddings=train_embeddings,
                        train_labels=train_labels,
                        train_mask=train_mask,
                        num_classes=len(protocol.class_names),
                        coverage_target=float(cfg["coverage_target"]),
                        alpha=float(cfg["alpha"]),
                        cpd_risk_target=float(cfg.get("cpd_risk_target", 0.15)),
                        max_prototypes_per_class=int(cfg.get("max_prototypes_per_class", 1)),
                        min_points_per_proto=int(cfg.get("min_points_per_proto", 16)),
                        prototype_bank_seed=stable_seed(seed, protocol_name, stage_idx, "pre_adapt_proto_bank"),
                        ova_gate=pre_adapt_gate,
                        soft_consensus_risk_target=float(cfg.get("soft_consensus_risk_target", cfg.get("cpd_risk_target", 0.15))),
                        benign_reclaim_risk_target=float(cfg.get("benign_reclaim_risk_target", 0.02)),
                        nonbenign_bridge_risk_target=float(cfg.get("nonbenign_bridge_risk_target", 0.08)),
                        knn_k=int(cfg.get("knn_k", 8)),
                    )
                    pre_adapt_review_selectors = None
                    pre_adapt_selector_summary = None
                    if bool(cfg.get("target_pseudo_review_selector_enabled", False)) and bool(cfg.get("review_selector_enabled", False)):
                        selector, selector_summary = fit_review_selector(
                            val_logits=val_logits_full,
                            val_embeddings=val_embeddings_full,
                            val_labels=val_labels_full,
                            calibrator=pre_adapt_calibrator,
                            ova_gate=pre_adapt_gate,
                            benign_target=float(
                                cfg.get(
                                    "target_pseudo_review_selector_benign_target",
                                    cfg.get("review_selector_benign_target", 0.25),
                                )
                            ),
                        )
                        pre_adapt_selector_summary = selector_summary
                        if selector is not None:
                            pre_adapt_review_selectors = {
                                "ova_gate_selective": selector,
                            }
                    target_clean_logits_all, target_clean_embeddings_all = infer_logits_embeddings(
                        model,
                        x=target_x,
                        edge_index=target_edge_index,
                    )
                    pseudo_outputs = build_method_outputs(
                        logits=target_clean_logits_all[flow_indices],
                        embeddings=target_clean_embeddings_all[flow_indices],
                        calibrator=pre_adapt_calibrator,
                        ova_gate=pre_adapt_gate,
                        review_selectors=pre_adapt_review_selectors,
                        target_adapt_momentum=float(cfg.get("target_adapt_momentum", 0.0)),
                        shift_reclaim_enabled=bool(cfg.get("shift_reclaim_enabled", False)),
                        shift_reclaim_momentum=(
                            float(cfg["shift_reclaim_momentum"])
                            if cfg.get("shift_reclaim_momentum") is not None
                            else None
                        ),
                        shift_min_cohort=int(cfg.get("shift_min_cohort", 8)),
                        shift_conf_quantile=float(cfg.get("shift_conf_quantile", 0.1)),
                        shift_ova_quantile=float(cfg.get("shift_ova_quantile", 0.1)),
                        shift_proto_quantile=float(cfg.get("shift_proto_quantile", 0.9)),
                        shift_multi_margin_quantile=float(cfg.get("shift_multi_margin_quantile", cfg.get("shift_conf_quantile", 0.1))),
                        shift_hybrid_gain_quantile=float(cfg.get("shift_hybrid_gain_quantile", 0.8)),
                        shift_hybrid_activation_coverage=float(cfg.get("shift_hybrid_activation_coverage", 0.12)),
                        shift_hybrid_require_knn=bool(cfg.get("shift_hybrid_require_knn", True)),
                        shift_hybrid_require_trust=bool(cfg.get("shift_hybrid_require_trust", False)),
                    )
                    configured_pseudo_methods = target_pseudo_methods(cfg)
                    pseudo_methods = [pseudo_method for pseudo_method in configured_pseudo_methods if pseudo_method in pseudo_outputs]
                    if not pseudo_methods:
                        raise KeyError(f"no available target pseudo methods from {configured_pseudo_methods}")
                    primary_method = str(pseudo_methods[0])
                    pseudo_accept_np = np.zeros_like(
                        np.asarray(pseudo_outputs[primary_method]["accept"], dtype=bool),
                        dtype=bool,
                    )
                    pseudo_pred_np = np.asarray(pseudo_outputs[primary_method]["pred"], dtype=np.int64).copy()
                    pseudo_best_score = np.full_like(
                        np.asarray(pseudo_outputs[primary_method]["score"], dtype=np.float64),
                        -np.inf,
                        dtype=np.float64,
                    )
                    for pseudo_method in pseudo_methods:
                        method_accept = np.asarray(pseudo_outputs[pseudo_method]["accept"], dtype=bool)
                        method_pred = np.asarray(pseudo_outputs[pseudo_method]["pred"], dtype=np.int64)
                        method_score = np.asarray(pseudo_outputs[pseudo_method]["score"], dtype=np.float64)
                        better = method_accept & ((~pseudo_accept_np) | (method_score > pseudo_best_score))
                        pseudo_pred_np[better] = method_pred[better]
                        pseudo_best_score[better] = method_score[better]
                        pseudo_accept_np |= method_accept
                    if bool(cfg.get("target_pseudo_nonbenign_only", False)):
                        pseudo_accept_np &= pseudo_pred_np != 0
                    stage_ratio_cap = _stage_scaled_ratio(
                        base_ratio=(
                            float(cfg["target_pseudo_max_ratio"])
                            if cfg.get("target_pseudo_max_ratio") is not None
                            else None
                        ),
                        stage_index=stage_idx,
                        growth=pseudo_ratio_growth,
                    )
                    if stage_ratio_cap is not None:
                        pseudo_accept_np = _cap_pseudo_ratio(
                            accept=pseudo_accept_np,
                            best_score=pseudo_best_score,
                            max_ratio=stage_ratio_cap,
                            total_count=flow_count,
                        )
                    pseudo_weight_np = np.ones_like(pseudo_best_score, dtype=np.float64)
                    if bool(cfg.get("target_confidence_weighted_pseudo", False)):
                        pseudo_weight_np = _normalized_pseudo_weights(
                            accept=pseudo_accept_np,
                            best_score=pseudo_best_score,
                            min_weight=float(cfg.get("target_confidence_min_weight", 0.25)),
                        )
                    else:
                        pseudo_weight_np[pseudo_accept_np] = 1.0
                    pseudo_mask_full = torch.zeros(protocol.target.graph.num_nodes, dtype=torch.bool)
                    pseudo_labels_full = torch.full((protocol.target.graph.num_nodes,), -100, dtype=torch.long)
                    pred_labels_full = torch.full((protocol.target.graph.num_nodes,), -100, dtype=torch.long)
                    pseudo_weight_full = torch.zeros(protocol.target.graph.num_nodes, dtype=torch.float32)
                    pseudo_mask_full[flow_indices] = torch.as_tensor(pseudo_accept_np, dtype=torch.bool)
                    pseudo_labels_full[flow_indices] = torch.as_tensor(pseudo_pred_np, dtype=torch.long)
                    pred_labels_full[flow_indices] = torch.as_tensor(pseudo_pred_np, dtype=torch.long)
                    pseudo_weight_full[flow_indices] = torch.as_tensor(pseudo_weight_np, dtype=torch.float32)
                    pseudo_soft_targets_full = None
                    if bool(cfg.get("target_confidence_soft_pseudo_enabled", False)):
                        soft_temp = max(float(cfg.get("target_confidence_soft_pseudo_temperature", 1.0)), 1e-6)
                        clean_probs = torch.softmax(target_clean_logits_all[flow_indices] / soft_temp, dim=1)
                        pseudo_soft_targets_full = torch.zeros(
                            (protocol.target.graph.num_nodes, int(clean_probs.shape[1])),
                            dtype=torch.float32,
                        )
                        pseudo_soft_targets_full[flow_indices] = clean_probs.detach().cpu().float()
                    uncertainty_mask = protocol.target.flow_mask & (~pseudo_mask_full)
                    if bool(cfg.get("target_uncertainty_nonbenign_only", True)):
                        uncertainty_mask &= pred_labels_full != 0
                    adapt_start = perf_counter()
                    model, stage_summary = adapt_with_target_confidence(
                        model,
                        source_x=protocol.source.graph.x_norm.float(),
                        source_edge_index=protocol.source.graph.edge_index.long(),
                        source_labels=protocol.source_labels,
                        source_train_mask=protocol.source_train_mask,
                        target_x=target_x,
                        target_edge_index=target_edge_index,
                        pseudo_labels=pseudo_labels_full,
                        pseudo_mask=pseudo_mask_full,
                        uncertainty_mask=uncertainty_mask,
                        num_classes=len(protocol.class_names),
                        epochs=int(cfg.get("target_confidence_adapt_epochs", 0)),
                        lr=float(cfg.get("target_confidence_adapt_lr", cfg["lr"])),
                        source_weight=float(cfg.get("target_confidence_source_weight", 1.0)),
                        pseudo_weight=float(cfg.get("target_confidence_pseudo_weight", 0.5)),
                        uncertainty_weight=float(cfg.get("target_confidence_uniform_weight", 0.05)),
                        edge_dropout_prob=float(cfg.get("train_edge_dropout", 0.0)),
                        pseudo_soft_targets=pseudo_soft_targets_full,
                        pseudo_sample_weights=pseudo_weight_full,
                        source_prototypes=pre_adapt_calibrator.prototypes,
                        source_prototype_bank=pre_adapt_calibrator.multi_prototypes,
                        source_prototype_labels=pre_adapt_calibrator.multi_prototype_labels,
                        prototype_weight=float(cfg.get("target_confidence_prototype_weight", 0.0)),
                        prototype_nonbenign_only=bool(cfg.get("target_confidence_prototype_nonbenign_only", True)),
                        prototype_margin_weight=float(cfg.get("target_confidence_prototype_margin_weight", 0.0)),
                        prototype_margin_value=float(cfg.get("target_confidence_prototype_margin_value", 0.15)),
                        prototype_margin_nonbenign_only=bool(
                            cfg.get("target_confidence_prototype_margin_nonbenign_only", True)
                        ),
                        uncertainty_repulsion_weight=float(
                            cfg.get("target_confidence_uncertainty_repulsion_weight", 0.0)
                        ),
                        uncertainty_repulsion_margin=float(
                            cfg.get("target_confidence_uncertainty_repulsion_margin", 0.2)
                        ),
                    )
                    stage_summary.update(
                        {
                            "stage_index": int(stage_idx + 1),
                            "stage_count": int(stage_count),
                            "pseudo_method": primary_method,
                            "pseudo_methods": pseudo_methods,
                            "pseudo_ratio": float(pseudo_mask_full.sum().item() / max(flow_count, 1)),
                            "pseudo_nonbenign_only": int(bool(cfg.get("target_pseudo_nonbenign_only", False))),
                            "pseudo_ratio_cap": float(stage_ratio_cap) if stage_ratio_cap is not None else 1.0,
                            "weighted_pseudo_mean": float(
                                pseudo_weight_full[pseudo_mask_full].mean().item() if int(pseudo_mask_full.sum().item()) > 0 else 0.0
                            ),
                            "pre_adapt_selector_ran": int(pre_adapt_selector_summary.get("ran", 0)) if pre_adapt_selector_summary else 0,
                            "pre_adapt_selector_candidate_fraction": float(
                                pre_adapt_selector_summary.get("candidate_fraction", 0.0)
                            ) if pre_adapt_selector_summary else 0.0,
                            "adapt_time_sec": float(perf_counter() - adapt_start),
                        }
                    )
                    stage_summaries.append(stage_summary)
                    source_infer_start = perf_counter()
                    src_logits, src_embeddings = infer_logits_embeddings(
                        model,
                        x=protocol.source.graph.x_norm.float(),
                        edge_index=protocol.source.graph.edge_index.long(),
                    )
                    source_infer_time_sec = float(perf_counter() - source_infer_start)
                    val_logits_full = src_logits[protocol.source_val_mask]
                    val_embeddings_full = src_embeddings[protocol.source_val_mask]
                    train_embeddings = src_embeddings
                    train_labels = protocol.source_labels
                    train_mask = protocol.source_train_mask
                    ova_fit_start = perf_counter()
                    ova_model = fit_ova_model(
                        train_embeddings=train_embeddings,
                        train_labels=train_labels,
                        train_mask=train_mask,
                        num_classes=len(protocol.class_names),
                    )
                    ova_fit_time_sec = float(perf_counter() - ova_fit_start)
                target_adapt_summary = dict(stage_summaries[-1]) if stage_summaries else {"ran": 0}
                target_adapt_summary["stage_summaries"] = stage_summaries
                save_json(protocol_dir / f"target_confidence_adapt_seed_{seed}.json", target_adapt_summary)

            target_eval_cache: dict[str, dict[str, object]] = {}
            target_inference_total_sec = 0.0
            for test_cfg in stress_tests:
                perturb_name = str(test_cfg["name"])
                perturb_edge_index, perturb_meta = apply_graph_perturbation(
                    edge_index=target_edge_index,
                    support_mask=support_mask,
                    perturbation_type=str(test_cfg["type"]),
                    rate=float(test_cfg["rate"]),
                    seed=stable_seed(seed, protocol_name, perturb_name),
                )
                target_infer_start = perf_counter()
                tgt_logits, tgt_embeddings = infer_logits_embeddings(
                    model,
                    x=target_x,
                    edge_index=perturb_edge_index,
                )
                target_infer_time_sec = float(perf_counter() - target_infer_start)
                target_inference_total_sec += target_infer_time_sec
                target_eval_cache[perturb_name] = {
                    "logits": tgt_logits[protocol.target_test_mask],
                    "embeddings": tgt_embeddings[protocol.target_test_mask],
                    "meta": perturb_meta,
                    "type": str(test_cfg["type"]),
                    "rate": float(test_cfg["rate"]),
                    "infer_time_sec": target_infer_time_sec,
                }
                perturb_row = {
                    "protocol": protocol_name,
                    "source": source_name,
                    "target": target_name,
                    "holdout_family": holdout_family,
                    "seed": int(seed),
                    "perturbation": perturb_name,
                    "perturbation_type": str(test_cfg["type"]),
                    "perturbation_rate": float(test_cfg["rate"]),
                    "target_infer_time_sec": target_infer_time_sec,
                    **perturb_meta,
                }
                perturbation_rows.append(perturb_row)
                protocol_perturbation_rows.append(perturb_row)

            calibration_total_sec = 0.0
            evaluation_total_sec = 0.0
            method_count = 0
            seed_curve_cache: dict[str, dict[str, np.ndarray]] = {}
            for bank_cfg in calibration_banks:
                bank_name = str(bank_cfg["name"])
                bank_fraction = float(bank_cfg["fraction"])
                bank_logits, bank_embeddings, bank_labels, bank_meta = subsample_calibration_bank(
                    val_logits=val_logits_full,
                    val_embeddings=val_embeddings_full,
                    val_labels=val_labels_full,
                    fraction=bank_fraction,
                    seed=stable_seed(seed, protocol_name, bank_name, "calibration_bank"),
                )
                calibration_start = perf_counter()
                ova_gate = None
                review_selectors = None
                if ova_model is not None:
                    ova_gate = calibrate_ova_gate(
                        ova_model=ova_model,
                        val_embeddings=bank_embeddings,
                        coverage_target=float(cfg["coverage_target"]),
                    )
                calibrator = fit_calibrator(
                    val_logits=bank_logits,
                    val_embeddings=bank_embeddings,
                    val_labels=bank_labels,
                    train_embeddings=train_embeddings,
                    train_labels=train_labels,
                    train_mask=train_mask,
                    num_classes=len(protocol.class_names),
                    coverage_target=float(cfg["coverage_target"]),
                    alpha=float(cfg["alpha"]),
                    cpd_risk_target=float(cfg.get("cpd_risk_target", 0.15)),
                    max_prototypes_per_class=int(cfg.get("max_prototypes_per_class", 1)),
                    min_points_per_proto=int(cfg.get("min_points_per_proto", 16)),
                    prototype_bank_seed=stable_seed(seed, protocol_name, bank_name, "proto_bank"),
                    ova_gate=ova_gate,
                    soft_consensus_risk_target=float(cfg.get("soft_consensus_risk_target", cfg.get("cpd_risk_target", 0.15))),
                    trust_consensus_risk_target=float(cfg.get("trust_consensus_risk_target", cfg.get("cpd_risk_target", 0.15))),
                    benign_reclaim_risk_target=float(cfg.get("benign_reclaim_risk_target", 0.02)),
                    nonbenign_bridge_risk_target=float(cfg.get("nonbenign_bridge_risk_target", 0.08)),
                    knn_k=int(cfg.get("knn_k", 8)),
                    trust_k=int(cfg.get("trust_k", cfg.get("knn_k", 8))),
                )
                calibration_time_sec = float(perf_counter() - calibration_start)
                calibration_total_sec += calibration_time_sec
                calibration_row = {
                    "protocol": protocol_name,
                    "source": source_name,
                    "target": target_name,
                    "holdout_family": holdout_family,
                    "seed": int(seed),
                    "calibration_bank": bank_name,
                    "calibration_fraction": bank_fraction,
                    "calibration_time_sec": calibration_time_sec,
                    "temperature": calibrator.temperature,
                    "aps_quantile": calibrator.aps_quantile,
                    "prototype_threshold": calibrator.prototype_threshold,
                    "prototype_thresholds": calibrator.prototype_thresholds,
                    "multi_proto_distance_threshold": calibrator.multi_proto_distance_threshold,
                    "multi_proto_distance_thresholds": calibrator.multi_proto_distance_thresholds,
                    "multi_proto_margin_threshold": calibrator.multi_proto_margin_threshold,
                    "multi_proto_margin_thresholds": calibrator.multi_proto_margin_thresholds,
                    "multi_proto_distance_scale": calibrator.multi_proto_distance_scale,
                    "multi_proto_margin_scale": calibrator.multi_proto_margin_scale,
                    "multi_proto_count": int(calibrator.multi_prototypes.shape[0]),
                    "knn_distance_threshold": calibrator.knn_distance_threshold,
                    "knn_distance_thresholds": calibrator.knn_distance_thresholds,
                    "knn_distance_scale": calibrator.knn_distance_scale,
                    "knn_k": calibrator.knn_k,
                    "trust_threshold": calibrator.trust_threshold,
                    "trust_thresholds": calibrator.trust_thresholds,
                    "trust_score_scale": calibrator.trust_score_scale,
                    "trust_k": calibrator.trust_k,
                    "confidence_threshold": calibrator.confidence_threshold,
                    "energy_threshold": calibrator.energy_threshold,
                    "coverage_target": calibrator.coverage_target,
                    "alpha": calibrator.alpha,
                    "cpd_threshold": calibrator.cpd_threshold,
                    "cpd_risk_target": calibrator.cpd_risk_target,
                    "cpd_conf_scale": calibrator.cpd_conf_scale,
                    "cpd_proto_scale": calibrator.cpd_proto_scale,
                    "cpd_val_coverage": calibrator.cpd_val_coverage,
                    "cpd_val_risk": calibrator.cpd_val_risk,
                    "ova_score_scale": calibrator.ova_score_scale,
                    "soft_consensus_threshold": calibrator.soft_consensus_threshold,
                    "soft_consensus_risk_target": calibrator.soft_consensus_risk_target,
                    "soft_consensus_val_coverage": calibrator.soft_consensus_val_coverage,
                    "soft_consensus_val_risk": calibrator.soft_consensus_val_risk,
                    "trust_consensus_threshold": calibrator.trust_consensus_threshold,
                    "trust_consensus_risk_target": calibrator.trust_consensus_risk_target,
                    "trust_consensus_val_coverage": calibrator.trust_consensus_val_coverage,
                    "trust_consensus_val_risk": calibrator.trust_consensus_val_risk,
                    "benign_reclaim_threshold": calibrator.benign_reclaim_threshold,
                    "benign_reclaim_risk_target": calibrator.benign_reclaim_risk_target,
                    "benign_reclaim_val_coverage": calibrator.benign_reclaim_val_coverage,
                    "benign_reclaim_val_risk": calibrator.benign_reclaim_val_risk,
                    "nonbenign_bridge_threshold": calibrator.nonbenign_bridge_threshold,
                    "nonbenign_bridge_risk_target": calibrator.nonbenign_bridge_risk_target,
                    "nonbenign_bridge_val_coverage": calibrator.nonbenign_bridge_val_coverage,
                    "nonbenign_bridge_val_risk": calibrator.nonbenign_bridge_val_risk,
                    **bank_meta,
                }
                if ova_gate is not None:
                    calibration_row["ova_threshold"] = float(ova_gate.threshold)
                if bool(cfg.get("review_selector_enabled", False)):
                    selector, selector_summary = fit_review_selector(
                        val_logits=bank_logits,
                        val_embeddings=bank_embeddings,
                        val_labels=bank_labels,
                        calibrator=calibrator,
                        ova_gate=ova_gate,
                        benign_target=float(cfg.get("review_selector_benign_target", 0.25)),
                    )
                    calibration_row.update(
                        {
                            "review_selector_enabled": 1,
                            "review_selector_ran": int(selector_summary.get("ran", 0)),
                            "review_selector_benign_target": float(cfg.get("review_selector_benign_target", 0.25)),
                            "review_selector_val_benign_review_rate": float(
                                selector_summary.get("val_benign_review_rate", 0.0)
                            ),
                            "review_selector_val_nonbenign_capture_rate": float(
                                selector_summary.get("val_nonbenign_capture_rate", 0.0)
                            ),
                        }
                    )
                    save_json(
                        protocol_dir / f"review_selector_seed_{seed}_{bank_name}.json",
                        {
                            "protocol": protocol_name,
                            "seed": int(seed),
                            "calibration_bank": bank_name,
                            "summary": selector_summary,
                            "weights": selector.weights if selector is not None else [],
                            "bias": float(selector.bias) if selector is not None else 0.0,
                            "feature_mean": selector.feature_mean if selector is not None else [],
                            "feature_scale": selector.feature_scale if selector is not None else [],
                        },
                    )
                    if selector is not None:
                        review_selectors = {
                            "ova_gate_selective": selector,
                        }
                calibration_rows.append(calibration_row)
                protocol_calibration_rows.append(calibration_row)
                save_json(protocol_dir / f"calibrator_seed_{seed}_{bank_name}.json", calibration_row)
                if ova_gate is not None:
                    save_json(
                        protocol_dir / f"ova_gate_seed_{seed}_{bank_name}.json",
                        {
                            "protocol": protocol_name,
                            "seed": int(seed),
                            "calibration_bank": bank_name,
                            "ova_threshold": float(ova_gate.threshold),
                            "weights": ova_gate.weights,
                            "bias": ova_gate.bias,
                        },
                    )

                for perturb_name, payload in target_eval_cache.items():
                    eval_start = perf_counter()
                    method_outputs = build_method_outputs(
                        logits=payload["logits"],
                        embeddings=payload["embeddings"],
                        calibrator=calibrator,
                        ova_gate=ova_gate,
                        review_selectors=review_selectors,
                        target_adapt_momentum=float(cfg.get("target_adapt_momentum", 0.0)),
                        shift_reclaim_enabled=bool(cfg.get("shift_reclaim_enabled", False)),
                        shift_reclaim_momentum=(
                            float(cfg["shift_reclaim_momentum"])
                            if cfg.get("shift_reclaim_momentum") is not None
                            else None
                        ),
                        shift_min_cohort=int(cfg.get("shift_min_cohort", 8)),
                        shift_conf_quantile=float(cfg.get("shift_conf_quantile", 0.1)),
                        shift_ova_quantile=float(cfg.get("shift_ova_quantile", 0.1)),
                        shift_proto_quantile=float(cfg.get("shift_proto_quantile", 0.9)),
                        shift_multi_margin_quantile=float(cfg.get("shift_multi_margin_quantile", cfg.get("shift_conf_quantile", 0.1))),
                        shift_hybrid_gain_quantile=float(cfg.get("shift_hybrid_gain_quantile", 0.8)),
                        shift_hybrid_activation_coverage=float(cfg.get("shift_hybrid_activation_coverage", 0.12)),
                        shift_hybrid_require_knn=bool(cfg.get("shift_hybrid_require_knn", True)),
                        shift_hybrid_require_trust=bool(cfg.get("shift_hybrid_require_trust", False)),
                    )
                    method_count = max(method_count, len(method_outputs))
                    for method, method_payload in method_outputs.items():
                        metrics = evaluate_method(
                            labels=test_labels,
                            pred=np.asarray(method_payload["pred"]),
                            accept=np.asarray(method_payload["accept"]),
                            score=np.asarray(method_payload["score"]),
                        )
                        metric_rows.append(
                            {
                                "protocol": protocol_name,
                                "source": source_name,
                                "target": target_name,
                                "holdout_family": holdout_family,
                                "seed": int(seed),
                                "method": method,
                                "calibration_bank": bank_name,
                                "calibration_fraction": bank_fraction,
                                "calibration_size": int(bank_meta["bank_size"]),
                                "calibration_fraction_realized": float(bank_meta["bank_fraction_realized"]),
                                "perturbation": perturb_name,
                                "perturbation_type": str(payload["type"]),
                                "perturbation_rate": float(payload["rate"]),
                                **metrics,
                            }
                        )
                        if bank_name == plot_bank and perturb_name == plot_perturbation:
                            coverage, risk, aurc = risk_coverage_curve(
                                labels=test_labels,
                                pred=np.asarray(method_payload["pred"]),
                                score=np.asarray(method_payload["score"]),
                            )
                            seed_curve_cache[method] = {
                                "coverage": coverage,
                                "risk": risk,
                                "aurc": np.asarray([aurc], dtype=np.float64),
                            }
                    triage_policies = [
                        ("triage_consensus_ova", "cpd_consensus", "ova_gate"),
                        ("triage_strict_ova", "cpd_strict", "ova_gate"),
                        ("triage_consensus_plus_ova", "cpd_consensus_plus", "ova_gate"),
                        ("triage_consensus_plus_ova_nonbenign", "cpd_consensus_plus", "ova_gate_nonbenign"),
                        ("triage_consensus_plus_msp_nonbenign", "cpd_consensus_plus", "msp_nonbenign"),
                        ("triage_consensus_plus_energy_nonbenign", "cpd_consensus_plus", "energy_nonbenign"),
                        ("triage_consensus_plus_prototype_nonbenign", "cpd_consensus_plus", "prototype_only_nonbenign"),
                        ("triage_consensus_plus_cpd_gate_nonbenign", "cpd_consensus_plus", "cpd_gate_nonbenign"),
                        ("triage_shift_consensus_plus_ova", "cpd_shift_consensus_plus", "ova_gate"),
                        ("triage_shift_consensus_plus_ova_nonbenign", "cpd_shift_consensus_plus", "ova_gate_nonbenign"),
                        ("triage_shift_consensus_plus_prototype_nonbenign", "cpd_shift_consensus_plus", "prototype_only_nonbenign"),
                        ("triage_soft_consensus_ova", "cpd_soft_consensus", "ova_gate"),
                        ("triage_soft_consensus_plus_ova", "cpd_soft_consensus_plus", "ova_gate"),
                        ("triage_soft_consensus_plus_ova_nonbenign", "cpd_soft_consensus_plus", "ova_gate_nonbenign"),
                        ("triage_soft_consensus_plus_ova_nonbenign_agree", "cpd_soft_consensus_plus", "ova_gate_nonbenign_agree"),
                        ("triage_trust_soft_consensus_plus_ova", "cpd_trust_soft_consensus_plus", "ova_gate"),
                        ("triage_trust_soft_consensus_plus_ova_nonbenign", "cpd_trust_soft_consensus_plus", "ova_gate_nonbenign"),
                        ("triage_shift_trust_soft_consensus_plus_ova_nonbenign", "cpd_shift_trust_soft_consensus_plus", "ova_gate_nonbenign"),
                        ("triage_trust_consensus_gate_plus_ova_nonbenign", "cpd_trust_consensus_gate_plus", "ova_gate_nonbenign"),
                        ("triage_proto_trust_consensus_gate_plus_ova_nonbenign", "cpd_proto_trust_consensus_gate_plus", "ova_gate_nonbenign"),
                        ("triage_knn_trust_consensus_gate_plus_ova_nonbenign", "cpd_knn_trust_consensus_gate_plus", "ova_gate_nonbenign"),
                        ("triage_shift_trust_consensus_gate_plus_ova_nonbenign", "cpd_shift_trust_consensus_gate_plus", "ova_gate_nonbenign"),
                        ("triage_shift_knn_trust_consensus_gate_plus_ova_nonbenign", "cpd_shift_knn_trust_consensus_gate_plus", "ova_gate_nonbenign"),
                        ("triage_knn_consensus_plus_ova_nonbenign", "cpd_knn_consensus_plus", "ova_gate_nonbenign"),
                        ("triage_knn_consensus_gate_plus_ova_nonbenign", "cpd_knn_consensus_gate_plus", "ova_gate_nonbenign"),
                        ("triage_proto_knn_consensus_gate_plus_ova_nonbenign", "cpd_proto_knn_consensus_gate_plus", "ova_gate_nonbenign"),
                        ("triage_soft_knn_consensus_plus_ova_nonbenign", "cpd_soft_knn_consensus_plus", "ova_gate_nonbenign"),
                    ]
                    if "cpd_multiproto_consensus_plus" in method_outputs:
                        triage_policies.append(
                            (
                                "triage_multiproto_consensus_plus_ova_nonbenign",
                                "cpd_multiproto_consensus_plus",
                                "ova_gate_nonbenign",
                            )
                        )
                    if "cpd_multiproto_consensus_gate_plus" in method_outputs:
                        triage_policies.append(
                            (
                                "triage_multiproto_consensus_gate_plus_ova_nonbenign",
                                "cpd_multiproto_consensus_gate_plus",
                                "ova_gate_nonbenign",
                            )
                        )
                    if "cpd_shift_multiproto_consensus_plus" in method_outputs:
                        triage_policies.append(
                            (
                                "triage_shift_multiproto_consensus_plus_ova_nonbenign",
                                "cpd_shift_multiproto_consensus_plus",
                                "ova_gate_nonbenign",
                            )
                        )
                    if "cpd_shift_multiproto_consensus_gate_plus" in method_outputs:
                        triage_policies.append(
                            (
                                "triage_shift_multiproto_consensus_gate_plus_ova_nonbenign",
                                "cpd_shift_multiproto_consensus_gate_plus",
                                "ova_gate_nonbenign",
                            )
                        )
                    if "cpd_shift_multiproto_coverage_switch_plus" in method_outputs:
                        triage_policies.append(
                            (
                                "triage_shift_multiproto_coverage_switch_plus_ova_nonbenign",
                                "cpd_shift_multiproto_coverage_switch_plus",
                                "ova_gate_nonbenign",
                            )
                        )
                    if "cpd_shift_multiproto_selective_gate_plus" in method_outputs:
                        triage_policies.append(
                            (
                                "triage_shift_multiproto_selective_gate_plus_ova_nonbenign",
                                "cpd_shift_multiproto_selective_gate_plus",
                                "ova_gate_nonbenign",
                            )
                        )
                    if "cpd_adapt_consensus" in method_outputs:
                        triage_policies.append(("triage_adapt_consensus_ova", "cpd_adapt_consensus", "ova_gate"))
                    if "ova_gate_selective" in method_outputs:
                        triage_policies.append(("triage_consensus_plus_ova_selective", "cpd_consensus_plus", "ova_gate_selective"))
                    if "review_prototype_or_ova_selective" in method_outputs:
                        triage_policies.append(
                            (
                                "triage_consensus_plus_prototype_or_ova_selective",
                                "cpd_consensus_plus",
                                "review_prototype_or_ova_selective",
                            )
                        )
                    if "review_prototype_or_ova_selective" in method_outputs:
                        triage_policies.append(
                            (
                                "triage_knn_consensus_plus_prototype_or_ova_selective",
                                "cpd_knn_consensus_plus",
                                "review_prototype_or_ova_selective",
                            )
                        )
                        triage_policies.append(
                            (
                                "triage_soft_knn_consensus_plus_prototype_or_ova_selective",
                                "cpd_soft_knn_consensus_plus",
                                "review_prototype_or_ova_selective",
                            )
                        )
                        triage_policies.append(
                            (
                                "triage_knn_consensus_gate_plus_prototype_or_ova_selective",
                                "cpd_knn_consensus_gate_plus",
                                "review_prototype_or_ova_selective",
                            )
                        )
                        triage_policies.append(
                            (
                                "triage_proto_knn_consensus_gate_plus_prototype_or_ova_selective",
                                "cpd_proto_knn_consensus_gate_plus",
                                "review_prototype_or_ova_selective",
                            )
                        )
                    for policy_name, auto_method, review_method in triage_policies:
                        if auto_method not in method_outputs or review_method not in method_outputs:
                            continue
                        triage_metrics = evaluate_triage_policy(
                            labels=test_labels,
                            auto_pred=np.asarray(method_outputs[auto_method]["pred"]),
                            auto_accept=np.asarray(method_outputs[auto_method]["accept"]),
                            review_pred=np.asarray(method_outputs[review_method]["pred"]),
                            review_accept=np.asarray(method_outputs[review_method]["accept"]),
                        )
                        triage_row = {
                            "protocol": protocol_name,
                            "source": source_name,
                            "target": target_name,
                            "holdout_family": holdout_family,
                            "seed": int(seed),
                            "policy": policy_name,
                            "auto_method": auto_method,
                            "review_method": review_method,
                            "calibration_bank": bank_name,
                            "calibration_fraction": bank_fraction,
                            "calibration_size": int(bank_meta["bank_size"]),
                            "calibration_fraction_realized": float(bank_meta["bank_fraction_realized"]),
                            "perturbation": perturb_name,
                            "perturbation_type": str(payload["type"]),
                            "perturbation_rate": float(payload["rate"]),
                            **triage_metrics,
                        }
                        triage_rows.append(triage_row)
                        protocol_triage_rows.append(triage_row)
                    evaluation_total_sec += float(perf_counter() - eval_start)
            curve_cache[protocol_name][str(seed)] = seed_curve_cache

            model_params = int(sum(parameter.numel() for parameter in model.parameters()))
            model_size_mb = float(4.0 * model_params / 1_000_000.0)
            active_clients = int(training_summary.get("active_clients", 0))
            rounds_completed = int(training_summary.get("rounds_completed", cfg["rounds"]))
            uplink_mb = float(model_size_mb * active_clients * rounds_completed)
            downlink_mb = float(model_size_mb * active_clients * rounds_completed)
            resource_row = {
                "protocol": protocol_name,
                "source": source_name,
                "target": target_name,
                "holdout_family": holdout_family,
                "seed": int(seed),
                "model_params": model_params,
                "model_size_mb": model_size_mb,
                "active_clients": active_clients,
                "rounds_completed": rounds_completed,
                "train_time_sec": train_time_sec,
                "source_infer_time_sec": source_infer_time_sec,
                "ova_fit_time_sec": ova_fit_time_sec,
                "calibration_total_time_sec": calibration_total_sec,
                "target_inference_total_time_sec": target_inference_total_sec,
                "evaluation_total_time_sec": evaluation_total_sec,
                "total_runtime_sec": train_time_sec
                + source_infer_time_sec
                + ova_fit_time_sec
                + calibration_total_sec
                + target_inference_total_sec
                + evaluation_total_sec,
                "uplink_mb": uplink_mb,
                "downlink_mb": downlink_mb,
                "total_comm_mb": float(uplink_mb + downlink_mb),
                "num_calibration_banks": len(calibration_banks),
                "num_perturbations": len(stress_tests),
                "num_methods": method_count,
            }
            resource_rows.append(resource_row)
            protocol_resource_rows.append(resource_row)

        protocol_rows = [row for row in metric_rows if str(row["protocol"]) == protocol_name]
        aggregated = aggregate_rows(
            protocol_rows,
            group_keys=[
                "protocol",
                "source",
                "target",
                "holdout_family",
                "calibration_bank",
                "calibration_fraction",
                "perturbation",
                "perturbation_type",
                "perturbation_rate",
                "method",
            ],
            metric_keys=[
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
            ],
        )
        protocol_summaries.extend(aggregated)
        write_rows_csv(protocol_dir / "seed_metrics.csv", protocol_rows)
        write_rows_csv(protocol_dir / "summary_metrics.csv", aggregated)
        write_rows_csv(protocol_dir / "resource_metrics.csv", protocol_resource_rows)
        if protocol_triage_rows:
            triage_aggregated = aggregate_rows(
                protocol_triage_rows,
                group_keys=[
                    "protocol",
                    "source",
                    "target",
                    "holdout_family",
                    "policy",
                    "auto_method",
                    "review_method",
                    "calibration_bank",
                    "calibration_fraction",
                    "perturbation",
                    "perturbation_type",
                    "perturbation_rate",
                ],
                metric_keys=[
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
                ],
            )
            write_rows_csv(protocol_dir / "triage_seed_metrics.csv", protocol_triage_rows)
            write_rows_csv(protocol_dir / "triage_summary_metrics.csv", triage_aggregated)
        write_rows_csv(protocol_dir / "calibration_metrics.csv", protocol_calibration_rows)
        write_rows_csv(protocol_dir / "perturbation_metrics.csv", protocol_perturbation_rows)

        first_seed = str(seeds[0])
        if curve_cache[protocol_name].get(first_seed):
            plot_risk_coverage(
                curve_cache[protocol_name][first_seed],
                protocol_dir / "risk_coverage_seed_first.png",
                title=f"{protocol_name}: risk-coverage ({plot_bank}, {plot_perturbation}, seed {first_seed})",
            )
        plot_rows = [
            row
            for row in aggregated
            if str(row["calibration_bank"]) == plot_bank and str(row["perturbation"]) == plot_perturbation
        ]
        if plot_rows:
            plot_unknown_routing(
                plot_rows,
                protocol_dir / "unknown_routing_summary.png",
                title=f"{protocol_name}: unknown routing ({plot_bank}, {plot_perturbation})",
            )

    save_json(run_dir / "curves.json", copy.deepcopy(curve_cache))
    write_rows_csv(run_dir / "all_seed_metrics.csv", metric_rows)
    write_rows_csv(run_dir / "all_summary_metrics.csv", protocol_summaries)
    if triage_rows:
        triage_aggregated = aggregate_rows(
            triage_rows,
            group_keys=[
                "protocol",
                "source",
                "target",
                "holdout_family",
                "policy",
                "auto_method",
                "review_method",
                "calibration_bank",
                "calibration_fraction",
                "perturbation",
                "perturbation_type",
                "perturbation_rate",
            ],
            metric_keys=[
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
            ],
        )
        write_rows_csv(run_dir / "triage_seed_metrics.csv", triage_rows)
        write_rows_csv(run_dir / "triage_summary_metrics.csv", triage_aggregated)
    write_rows_csv(run_dir / "resource_metrics.csv", resource_rows)
    write_rows_csv(run_dir / "calibration_metrics.csv", calibration_rows)
    write_rows_csv(run_dir / "perturbation_metrics.csv", perturbation_rows)
    save_json(
        run_dir / "run_manifest.json",
        {
            "run_dir": str(run_dir),
            "graph_root": str(graph_root),
            "scenario_graphs": resolved_scenarios,
            "protocols": list(curve_cache.keys()),
            "seeds": seeds,
            "calibration_banks": calibration_banks,
            "stress_tests": stress_tests,
            "include_ova_gate": include_ova_gate,
        },
    )
    print(f"[OK] OpenFedBot run completed: {run_dir}")


if __name__ == "__main__":
    main()
