from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch

from .schema import load_validated_graph_bundle


@dataclass
class ScenarioBundle:
    name: str
    graph_file: Path
    manifest_file: Path
    graph: Any
    flow_mask: torch.Tensor
    train_mask: torch.Tensor
    val_mask: torch.Tensor
    test_mask: torch.Tensor
    family_by_ip: dict[int, str]
    node_family: np.ndarray


@dataclass
class ProtocolData:
    source: ScenarioBundle
    target: ScenarioBundle
    class_names: list[str]
    known_families: list[str]
    holdout_family: str
    source_labels: torch.Tensor
    source_train_mask: torch.Tensor
    source_val_mask: torch.Tensor
    source_test_mask: torch.Tensor
    target_labels: torch.Tensor
    target_test_mask: torch.Tensor


def temporal_split(window_idx: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    valid = window_idx[window_idx >= 0]
    w_min = int(valid.min().item())
    w_max = int(valid.max().item())
    span = max(w_max - w_min + 1, 1)
    tr_end = w_min + int(0.6 * span)
    va_end = w_min + int(0.8 * span)
    train = (window_idx >= w_min) & (window_idx < tr_end)
    val = (window_idx >= tr_end) & (window_idx < va_end)
    test = window_idx >= va_end
    return train, val, test


def parse_role_family(role: str) -> str:
    text = str(role).strip()
    if not text:
        return "unknown"
    if text == "target":
        return "target"
    if text == "benign_user":
        return "benign"
    if text.startswith("bot:"):
        return text.split(":", 1)[1]
    return text


def load_scenario_bundle(
    name: str,
    graph_file: str | Path,
    *,
    manifest_file: str | Path | None = None,
) -> ScenarioBundle:
    graph_path = Path(graph_file).expanduser().resolve()
    graph, manifest, report = load_validated_graph_bundle(
        graph_path=graph_path,
        manifest_path=manifest_file,
    )
    flow_mask = (graph.window_idx >= 0) & (graph.ip_idx >= 0)
    if hasattr(graph, "temporal_train_mask") and hasattr(graph, "val_mask") and hasattr(graph, "test_mask"):
        train_mask = graph.temporal_train_mask.clone().bool()
        val_mask = graph.val_mask.clone().bool()
        test_mask = graph.test_mask.clone().bool()
    else:
        train_mask, val_mask, test_mask = temporal_split(graph.window_idx)
    train_mask &= flow_mask
    val_mask &= flow_mask
    test_mask &= flow_mask

    assert report.manifest_path is not None
    manifest_path = report.manifest_path
    role_by_ip = {str(ip): parse_role_family(role) for ip, role in dict(manifest.get("roles", {})).items()}

    family_by_ip: dict[int, str] = {}
    for ip_index, ip in enumerate(list(getattr(graph, "source_ips", []))):
        family_by_ip[int(ip_index)] = role_by_ip.get(str(ip), "unknown")

    node_family = np.asarray(
        [
            "support" if int(ip_index) < 0 else family_by_ip.get(int(ip_index), "unknown")
            for ip_index in graph.ip_idx.detach().cpu().tolist()
        ],
        dtype=object,
    )
    return ScenarioBundle(
        name=name,
        graph_file=graph_path,
        manifest_file=manifest_path,
        graph=graph,
        flow_mask=flow_mask,
        train_mask=train_mask,
        val_mask=val_mask,
        test_mask=test_mask,
        family_by_ip=family_by_ip,
        node_family=node_family,
    )


def list_bot_families(bundle: ScenarioBundle) -> list[str]:
    families = sorted({str(x) for x in bundle.node_family.tolist() if str(x) not in {"support", "unknown", "target", "benign"}})
    return families


def build_multiclass_labels(bundle: ScenarioBundle, known_families: list[str], holdout_family: str) -> torch.Tensor:
    labels = torch.full((bundle.graph.num_nodes,), -100, dtype=torch.long)
    family_to_label = {"benign": 0}
    for offset, family in enumerate(known_families, start=1):
        family_to_label[str(family)] = offset
    flow_indices = torch.nonzero(bundle.flow_mask, as_tuple=False).view(-1).tolist()
    for node_index in flow_indices:
        family = str(bundle.node_family[int(node_index)])
        if family == holdout_family:
            labels[int(node_index)] = -1
        elif family in family_to_label:
            labels[int(node_index)] = int(family_to_label[family])
    return labels


def build_protocol_data(
    *,
    source: ScenarioBundle,
    target: ScenarioBundle,
    holdout_family: str,
    target_mode: str,
) -> ProtocolData:
    source_families = list_bot_families(source)
    known_families = [family for family in source_families if family != holdout_family]
    class_names = ["benign"] + known_families

    source_labels = build_multiclass_labels(source, known_families=known_families, holdout_family=holdout_family)
    source_train_mask = source.train_mask & (source_labels >= 0)
    source_val_mask = source.val_mask & (source_labels >= 0)
    source_test_mask = source.test_mask & ((source_labels >= 0) | (source_labels == -1))

    target_labels = build_multiclass_labels(target, known_families=known_families, holdout_family=holdout_family)
    if target_mode == "temporal_test":
        target_test_mask = target.test_mask & ((target_labels >= 0) | (target_labels == -1))
    elif target_mode == "all_flow":
        target_test_mask = target.flow_mask & ((target_labels >= 0) | (target_labels == -1))
    else:
        raise KeyError(f"unknown target_mode: {target_mode}")

    return ProtocolData(
        source=source,
        target=target,
        class_names=class_names,
        known_families=known_families,
        holdout_family=holdout_family,
        source_labels=source_labels,
        source_train_mask=source_train_mask,
        source_val_mask=source_val_mask,
        source_test_mask=source_test_mask,
        target_labels=target_labels,
        target_test_mask=target_test_mask,
    )


def assign_ip_records_to_clients(
    ip_records: list[dict[str, Any]],
    *,
    num_clients: int,
    partition_mode: str,
    seed: int,
) -> list[list[dict[str, Any]]]:
    clients: list[list[dict[str, Any]]] = [[] for _ in range(int(num_clients))]
    if not ip_records:
        return clients
    rng = np.random.default_rng(int(seed))
    if partition_mode == "iid_lite":
        shuffled = list(ip_records)
        rng.shuffle(shuffled)
        loads = [0] * int(num_clients)
        for record in sorted(shuffled, key=lambda item: (-int(item["train_nodes"]), int(item["ip_index"]))):
            cid = min(range(int(num_clients)), key=lambda idx: (loads[idx], idx))
            clients[cid].append(record)
            loads[cid] += int(record["train_nodes"])
        return clients

    if partition_mode != "topology_noniid":
        raise KeyError(f"unknown partition mode: {partition_mode}")
    ordered = sorted(ip_records, key=lambda item: (str(item["family"]), int(item["ip_index"])))
    chunks = np.array_split(np.asarray(ordered, dtype=object), int(num_clients))
    for cid, chunk in enumerate(chunks):
        clients[cid] = [dict(item) for item in chunk.tolist()]
    return clients


def induce_local_subgraph(visible_mask: torch.Tensor, edge_index: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    local_nodes = torch.nonzero(visible_mask, as_tuple=False).view(-1)
    relabel = torch.full((int(visible_mask.numel()),), -1, dtype=torch.long)
    relabel[local_nodes] = torch.arange(local_nodes.numel(), dtype=torch.long)
    keep_edges = visible_mask[edge_index[0]] & visible_mask[edge_index[1]]
    local_edge_index = relabel[edge_index[:, keep_edges]]
    return local_nodes, local_edge_index


def build_client_views(
    *,
    bundle: ScenarioBundle,
    labels: torch.Tensor,
    train_mask: torch.Tensor,
    num_clients: int,
    partition_mode: str,
    seed: int,
) -> list[dict[str, Any]]:
    graph = bundle.graph
    support_mask = graph.ip_idx < 0
    ip_records: list[dict[str, Any]] = []
    for ip_index, family in sorted(bundle.family_by_ip.items()):
        ip_mask = graph.ip_idx == int(ip_index)
        train_nodes = int((ip_mask & train_mask).sum().item())
        total_flow_nodes = int((ip_mask & bundle.flow_mask).sum().item())
        if total_flow_nodes <= 0:
            continue
        ip_records.append(
            {
                "ip_index": int(ip_index),
                "family": str(family),
                "train_nodes": int(train_nodes),
                "total_flow_nodes": int(total_flow_nodes),
            }
        )

    assigned = assign_ip_records_to_clients(
        ip_records,
        num_clients=num_clients,
        partition_mode=partition_mode,
        seed=seed,
    )
    x = graph.x_norm.float()
    edge_index = graph.edge_index.long()
    views: list[dict[str, Any]] = []
    for cid, records in enumerate(assigned):
        owned_ip_indices = sorted(int(item["ip_index"]) for item in records)
        owned_mask = torch.zeros(graph.num_nodes, dtype=torch.bool)
        for ip_index in owned_ip_indices:
            owned_mask |= graph.ip_idx == int(ip_index)
        visible_mask = support_mask | owned_mask
        local_nodes, local_edge_index = induce_local_subgraph(visible_mask, edge_index)
        local_train_mask = train_mask[local_nodes]
        views.append(
            {
                "client_id": int(cid),
                "x": x[local_nodes],
                "edge_index": local_edge_index,
                "labels": labels[local_nodes],
                "train_mask": local_train_mask,
                "train_nodes": int(local_train_mask.sum().item()),
                "owned_ip_indices": owned_ip_indices,
            }
        )
    return views


def scenario_counts(bundle: ScenarioBundle, labels: torch.Tensor, test_mask: torch.Tensor) -> dict[str, int]:
    return {
        "total_test_nodes": int(test_mask.sum().item()),
        "known_nodes": int(((labels >= 0) & test_mask).sum().item()),
        "unknown_nodes": int(((labels == -1) & test_mask).sum().item()),
        "benign_nodes": int(((labels == 0) & test_mask).sum().item()),
        "known_bot_nodes": int(((labels > 0) & test_mask).sum().item()),
    }
