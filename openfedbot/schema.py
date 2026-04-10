from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch


GRAPH_SCHEMA_VERSION = "openfedbot-graph-v1"
REQUIRED_GRAPH_FIELDS = (
    "x_norm",
    "edge_index",
    "window_idx",
    "ip_idx",
    "source_ips",
)
OPTIONAL_MASK_FIELDS = (
    "temporal_train_mask",
    "val_mask",
    "test_mask",
)


@dataclass
class GraphContractReport:
    graph_path: Path
    manifest_path: Path | None
    num_nodes: int
    num_edges: int
    num_features: int
    source_ip_count: int
    observed_schema_version: str
    errors: list[str]
    warnings: list[str]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def _is_tensor_vector(value: Any) -> bool:
    return isinstance(value, torch.Tensor) and int(value.dim()) == 1


def _load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def resolve_manifest_path(
    *,
    graph_path: str | Path,
    graph: Any,
    explicit_manifest_path: str | Path | None = None,
) -> Path | None:
    if explicit_manifest_path is not None:
        return Path(explicit_manifest_path).expanduser().resolve()
    manifest_attr = getattr(graph, "manifest_file", "")
    if str(manifest_attr).strip():
        return Path(str(manifest_attr)).expanduser().resolve()
    return None


def validate_graph_contract(
    *,
    graph: Any,
    graph_path: str | Path,
    manifest: dict[str, Any] | None,
    manifest_path: str | Path | None,
) -> GraphContractReport:
    graph_path_obj = Path(graph_path).expanduser().resolve()
    manifest_path_obj = Path(manifest_path).expanduser().resolve() if manifest_path is not None else None
    errors: list[str] = []
    warnings: list[str] = []

    for field_name in REQUIRED_GRAPH_FIELDS:
        if not hasattr(graph, field_name):
            errors.append(f"missing required graph field: {field_name}")

    if errors:
        return GraphContractReport(
            graph_path=graph_path_obj,
            manifest_path=manifest_path_obj,
            num_nodes=0,
            num_edges=0,
            num_features=0,
            source_ip_count=0,
            observed_schema_version="",
            errors=errors,
            warnings=warnings,
        )

    x_norm = getattr(graph, "x_norm")
    edge_index = getattr(graph, "edge_index")
    window_idx = getattr(graph, "window_idx")
    ip_idx = getattr(graph, "ip_idx")
    source_ips = list(getattr(graph, "source_ips"))

    if not isinstance(x_norm, torch.Tensor) or int(x_norm.dim()) != 2:
        errors.append("x_norm must be a rank-2 torch.Tensor")
    if not isinstance(edge_index, torch.Tensor) or int(edge_index.dim()) != 2 or int(edge_index.shape[0]) != 2:
        errors.append("edge_index must be a rank-2 torch.Tensor with shape [2, E]")
    if not _is_tensor_vector(window_idx):
        errors.append("window_idx must be a rank-1 torch.Tensor")
    if not _is_tensor_vector(ip_idx):
        errors.append("ip_idx must be a rank-1 torch.Tensor")

    num_nodes = int(x_norm.shape[0]) if isinstance(x_norm, torch.Tensor) and int(x_norm.dim()) == 2 else 0
    num_edges = int(edge_index.shape[1]) if isinstance(edge_index, torch.Tensor) and int(edge_index.dim()) == 2 else 0
    num_features = int(x_norm.shape[1]) if isinstance(x_norm, torch.Tensor) and int(x_norm.dim()) == 2 else 0

    if _is_tensor_vector(window_idx) and int(window_idx.shape[0]) != num_nodes:
        errors.append("window_idx length must match x_norm.shape[0]")
    if _is_tensor_vector(ip_idx) and int(ip_idx.shape[0]) != num_nodes:
        errors.append("ip_idx length must match x_norm.shape[0]")
    if isinstance(edge_index, torch.Tensor) and int(edge_index.dim()) == 2 and int(edge_index.shape[0]) == 2 and num_nodes > 0:
        if int(edge_index.numel()) > 0:
            min_index = int(edge_index.min().item())
            max_index = int(edge_index.max().item())
            if min_index < 0 or max_index >= num_nodes:
                errors.append("edge_index contains node ids outside [0, num_nodes)")

    for field_name in OPTIONAL_MASK_FIELDS:
        if hasattr(graph, field_name):
            value = getattr(graph, field_name)
            if not _is_tensor_vector(value):
                errors.append(f"{field_name} must be a rank-1 torch.Tensor when present")
            elif int(value.shape[0]) != num_nodes:
                errors.append(f"{field_name} length must match x_norm.shape[0]")

    schema_version = str(getattr(graph, "graph_schema_version", "") or "")
    if not schema_version:
        warnings.append("graph_schema_version is missing; treating graph as a legacy-compatible bundle")
    elif schema_version != GRAPH_SCHEMA_VERSION:
        warnings.append(
            f"graph_schema_version={schema_version!r} differs from expected {GRAPH_SCHEMA_VERSION!r}"
        )

    if not source_ips:
        errors.append("source_ips must be a non-empty sequence")

    if manifest is None:
        errors.append("manifest file is required either via graph.manifest_file or explicit manifest_path")
    else:
        roles = manifest.get("roles")
        if not isinstance(roles, dict):
            errors.append("manifest must contain a roles mapping")
        else:
            missing_roles = [str(ip) for ip in source_ips if str(ip) not in roles]
            if missing_roles:
                warnings.append(f"{len(missing_roles)} source_ips do not have explicit role assignments")

    return GraphContractReport(
        graph_path=graph_path_obj,
        manifest_path=manifest_path_obj,
        num_nodes=num_nodes,
        num_edges=num_edges,
        num_features=num_features,
        source_ip_count=len(source_ips),
        observed_schema_version=schema_version,
        errors=errors,
        warnings=warnings,
    )


def load_validated_graph_bundle(
    *,
    graph_path: str | Path,
    manifest_path: str | Path | None = None,
) -> tuple[Any, dict[str, Any], GraphContractReport]:
    graph_path_obj = Path(graph_path).expanduser().resolve()
    graph = torch.load(graph_path_obj, weights_only=False, map_location="cpu")
    resolved_manifest_path = resolve_manifest_path(
        graph_path=graph_path_obj,
        graph=graph,
        explicit_manifest_path=manifest_path,
    )
    manifest = _load_manifest(resolved_manifest_path) if resolved_manifest_path is not None else None
    report = validate_graph_contract(
        graph=graph,
        graph_path=graph_path_obj,
        manifest=manifest,
        manifest_path=resolved_manifest_path,
    )
    if not report.is_valid:
        joined = "\n".join(f"- {item}" for item in report.errors)
        raise ValueError(f"graph contract validation failed for {graph_path_obj}:\n{joined}")
    assert manifest is not None
    return graph, manifest, report
