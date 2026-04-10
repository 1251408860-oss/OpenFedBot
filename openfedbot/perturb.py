from __future__ import annotations

from typing import Any

import numpy as np
import torch


def apply_graph_perturbation(
    *,
    edge_index: torch.Tensor,
    support_mask: torch.Tensor,
    perturbation_type: str,
    rate: float,
    seed: int,
) -> tuple[torch.Tensor, dict[str, Any]]:
    edge_index = edge_index.detach().cpu().long()
    support_mask = support_mask.detach().cpu().bool()
    num_edges = int(edge_index.shape[1])
    flow_context_mask = (~support_mask[edge_index[0]]) & (~support_mask[edge_index[1]])
    boundary_edges_before = int(flow_context_mask.sum().item())

    kind = str(perturbation_type)
    drop_rate = min(max(float(rate), 0.0), 1.0)
    if kind == "clean" or drop_rate <= 0.0 or num_edges <= 0:
        return edge_index, {
            "perturbation_type": kind,
            "requested_rate": drop_rate,
            "actual_drop_rate": 0.0,
            "num_edges_before": num_edges,
            "num_edges_after": num_edges,
            "boundary_edges_before": boundary_edges_before,
            "boundary_edges_after": boundary_edges_before,
        }

    if kind == "edge_dropout":
        eligible_mask = np.ones(num_edges, dtype=bool)
    elif kind == "boundary_dropout":
        # In these Ca-Bench graphs, support nodes are sinks only. The informative
        # message-passing neighborhood for flow nodes lives on flow->flow edges.
        eligible_mask = flow_context_mask.detach().cpu().numpy().astype(bool, copy=False)
    else:
        raise KeyError(f"unknown perturbation_type: {kind}")

    eligible_idx = np.flatnonzero(eligible_mask)
    if eligible_idx.size <= 0:
        return edge_index, {
            "perturbation_type": kind,
            "requested_rate": drop_rate,
            "actual_drop_rate": 0.0,
            "num_edges_before": num_edges,
            "num_edges_after": num_edges,
            "boundary_edges_before": boundary_edges_before,
            "boundary_edges_after": boundary_edges_before,
        }

    rng = np.random.default_rng(int(seed))
    sampled_drop = rng.random(eligible_idx.size) < drop_rate
    drop_mask = np.zeros(num_edges, dtype=bool)
    drop_mask[eligible_idx] = sampled_drop
    if bool(np.all(drop_mask)):
        drop_mask[int(eligible_idx[-1])] = False

    keep_mask = torch.from_numpy(~drop_mask)
    perturbed = edge_index[:, keep_mask]
    boundary_after = (~support_mask[perturbed[0]]) & (~support_mask[perturbed[1]])
    return perturbed, {
        "perturbation_type": kind,
        "requested_rate": drop_rate,
        "actual_drop_rate": float(sampled_drop.mean()) if sampled_drop.size > 0 else 0.0,
        "num_edges_before": num_edges,
        "num_edges_after": int(perturbed.shape[1]),
        "boundary_edges_before": boundary_edges_before,
        "boundary_edges_after": int(boundary_after.sum().item()),
    }
