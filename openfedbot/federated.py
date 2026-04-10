from __future__ import annotations

import copy
import random
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.metrics import f1_score

from .model import GraphSAGEClassifier


def set_random_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def build_class_weights(labels: torch.Tensor, mask: torch.Tensor, num_classes: int) -> torch.Tensor:
    counts = torch.bincount(labels[mask], minlength=num_classes).float()
    counts = torch.where(counts > 0, counts, torch.ones_like(counts))
    total = float(counts.sum().item())
    weights = total / (float(num_classes) * counts)
    return weights


def train_supervised(
    model: GraphSAGEClassifier,
    *,
    x: torch.Tensor,
    edge_index: torch.Tensor,
    labels: torch.Tensor,
    mask: torch.Tensor,
    epochs: int,
    lr: float,
    num_classes: int,
    edge_dropout_prob: float = 0.0,
    center_loss_weight: float = 0.0,
    center_margin_weight: float = 0.0,
    center_margin_value: float = 0.15,
) -> GraphSAGEClassifier:
    out = copy.deepcopy(model)
    if int(mask.sum().item()) <= 0:
        return out
    out.train()
    optimizer = torch.optim.Adam(out.parameters(), lr=float(lr))
    class_weights = build_class_weights(labels=labels, mask=mask, num_classes=num_classes)
    for _ in range(int(epochs)):
        optimizer.zero_grad()
        train_edge_index = edge_index
        drop_prob = min(max(float(edge_dropout_prob), 0.0), 0.95)
        if drop_prob > 0.0 and int(edge_index.shape[1]) > 1:
            keep_mask = torch.rand(int(edge_index.shape[1])) >= drop_prob
            if int(keep_mask.sum().item()) <= 0:
                keep_mask[0] = True
            train_edge_index = edge_index[:, keep_mask]
        logits, embeddings = out(x, train_edge_index, return_embeddings=True)
        loss = F.cross_entropy(logits[mask], labels[mask], weight=class_weights)
        if float(center_loss_weight) > 0.0 or float(center_margin_weight) > 0.0:
            masked_embeddings = F.normalize(embeddings[mask], dim=1)
            masked_labels = labels[mask]
            unique_classes = torch.unique(masked_labels)
            class_losses: list[torch.Tensor] = []
            class_centers: list[torch.Tensor] = []
            class_ids: list[int] = []
            for class_id in unique_classes.tolist():
                class_mask = masked_labels == int(class_id)
                if int(class_mask.sum().item()) <= 0:
                    continue
                center = F.normalize(masked_embeddings[class_mask].mean(dim=0, keepdim=True), dim=1)
                class_centers.append(center)
                class_ids.append(int(class_id))
                class_losses.append(1.0 - (masked_embeddings[class_mask] * center).sum(dim=1))
            if float(center_loss_weight) > 0.0 and class_losses:
                center_loss = torch.cat(class_losses, dim=0).mean()
                loss = loss + float(center_loss_weight) * center_loss
            if float(center_margin_weight) > 0.0 and len(class_centers) >= 2:
                stacked_centers = torch.cat(class_centers, dim=0)
                center_id_map = {class_id: idx for idx, class_id in enumerate(class_ids)}
                sample_center_idx = torch.as_tensor(
                    [center_id_map[int(item)] for item in masked_labels.detach().cpu().tolist()],
                    dtype=torch.long,
                    device=masked_embeddings.device,
                )
                similarities = masked_embeddings @ stacked_centers.T
                positive_sim = similarities.gather(1, sample_center_idx.view(-1, 1)).squeeze(1)
                negative_sim = similarities.clone()
                negative_sim.scatter_(1, sample_center_idx.view(-1, 1), float("-inf"))
                hardest_negative = negative_sim.max(dim=1).values
                center_margin_loss = F.relu(float(center_margin_value) - (positive_sim - hardest_negative)).mean()
                loss = loss + float(center_margin_weight) * center_margin_loss
        loss.backward()
        optimizer.step()
    return out


def finetune_group_dro(
    model: GraphSAGEClassifier,
    *,
    x: torch.Tensor,
    edge_index: torch.Tensor,
    labels: torch.Tensor,
    mask: torch.Tensor,
    group_ids: torch.Tensor,
    epochs: int,
    lr: float,
    num_classes: int,
    val_mask: torch.Tensor | None = None,
    group_dro_eta: float = 0.1,
    edge_dropout_prob: float = 0.0,
    center_loss_weight: float = 0.0,
    center_margin_weight: float = 0.0,
    center_margin_value: float = 0.15,
) -> tuple[GraphSAGEClassifier, dict[str, Any]]:
    out = copy.deepcopy(model)
    active_mask = mask.clone().bool()
    if int(active_mask.sum().item()) <= 0 or int(epochs) <= 0:
        return out, {
            "ran": 0,
            "epochs": int(max(epochs, 0)),
            "group_count": 0,
        }

    train_group_ids = group_ids[active_mask].detach().cpu().numpy().astype(np.int64, copy=False)
    unique_groups = sorted(np.unique(train_group_ids).tolist())
    if not unique_groups:
        return out, {
            "ran": 0,
            "epochs": int(max(epochs, 0)),
            "group_count": 0,
            "reason": "no_active_groups",
        }

    out.train()
    optimizer = torch.optim.Adam(out.parameters(), lr=float(lr))
    class_weights = build_class_weights(labels=labels, mask=active_mask, num_classes=num_classes)
    masked_group_ids = group_ids[active_mask]
    q = np.full((len(unique_groups),), 1.0 / max(len(unique_groups), 1), dtype=np.float64)
    best_state = copy.deepcopy(out.state_dict())
    best_val = (
        evaluate_known_split(
            out,
            x=x,
            edge_index=edge_index,
            labels=labels,
            mask=val_mask,
            num_classes=num_classes,
        )
        if val_mask is not None and int(val_mask.sum().item()) > 0
        else {"loss": 0.0, "accuracy": 0.0, "macro_f1": 0.0}
    )
    best_epoch = 0
    history: list[dict[str, float | int]] = []
    last_group_losses = np.zeros((len(unique_groups),), dtype=np.float64)

    for epoch_idx in range(1, int(epochs) + 1):
        optimizer.zero_grad()
        train_edge_index = edge_index
        drop_prob = min(max(float(edge_dropout_prob), 0.0), 0.95)
        if drop_prob > 0.0 and int(edge_index.shape[1]) > 1:
            keep_mask = torch.rand(int(edge_index.shape[1])) >= drop_prob
            if int(keep_mask.sum().item()) <= 0:
                keep_mask[0] = True
            train_edge_index = edge_index[:, keep_mask]
        logits, embeddings = out(x, train_edge_index, return_embeddings=True)
        per_sample_loss = F.cross_entropy(
            logits[active_mask],
            labels[active_mask],
            weight=class_weights,
            reduction="none",
        )
        group_losses: list[torch.Tensor] = []
        for group_id in unique_groups:
            group_mask = masked_group_ids == int(group_id)
            if int(group_mask.sum().item()) <= 0:
                group_losses.append(per_sample_loss.new_tensor(0.0))
                continue
            group_losses.append(per_sample_loss[group_mask].mean())
        group_losses_tensor = torch.stack(group_losses, dim=0)
        last_group_losses = group_losses_tensor.detach().cpu().numpy().astype(np.float64, copy=False)
        q = q * np.exp(float(group_dro_eta) * last_group_losses)
        q = q / max(float(q.sum()), 1e-12)
        q_tensor = torch.as_tensor(q, dtype=group_losses_tensor.dtype, device=group_losses_tensor.device)
        loss = (group_losses_tensor * q_tensor).sum()

        if float(center_loss_weight) > 0.0 or float(center_margin_weight) > 0.0:
            masked_embeddings = F.normalize(embeddings[active_mask], dim=1)
            masked_labels = labels[active_mask]
            unique_classes = torch.unique(masked_labels)
            class_losses: list[torch.Tensor] = []
            class_centers: list[torch.Tensor] = []
            class_ids: list[int] = []
            for class_id in unique_classes.tolist():
                class_mask = masked_labels == int(class_id)
                if int(class_mask.sum().item()) <= 0:
                    continue
                center = F.normalize(masked_embeddings[class_mask].mean(dim=0, keepdim=True), dim=1)
                class_centers.append(center)
                class_ids.append(int(class_id))
                class_losses.append(1.0 - (masked_embeddings[class_mask] * center).sum(dim=1))
            if float(center_loss_weight) > 0.0 and class_losses:
                center_loss = torch.cat(class_losses, dim=0).mean()
                loss = loss + float(center_loss_weight) * center_loss
            if float(center_margin_weight) > 0.0 and len(class_centers) >= 2:
                stacked_centers = torch.cat(class_centers, dim=0)
                center_id_map = {class_id: idx for idx, class_id in enumerate(class_ids)}
                sample_center_idx = torch.as_tensor(
                    [center_id_map[int(item)] for item in masked_labels.detach().cpu().tolist()],
                    dtype=torch.long,
                    device=masked_embeddings.device,
                )
                similarities = masked_embeddings @ stacked_centers.T
                positive_sim = similarities.gather(1, sample_center_idx.view(-1, 1)).squeeze(1)
                negative_sim = similarities.clone()
                negative_sim.scatter_(1, sample_center_idx.view(-1, 1), float("-inf"))
                hardest_negative = negative_sim.max(dim=1).values
                center_margin_loss = F.relu(float(center_margin_value) - (positive_sim - hardest_negative)).mean()
                loss = loss + float(center_margin_weight) * center_margin_loss

        loss.backward()
        optimizer.step()
        val_metrics = (
            evaluate_known_split(
                out,
                x=x,
                edge_index=edge_index,
                labels=labels,
                mask=val_mask,
                num_classes=num_classes,
            )
            if val_mask is not None and int(val_mask.sum().item()) > 0
            else {"loss": 0.0, "accuracy": 0.0, "macro_f1": 0.0}
        )
        history.append(
            {
                "epoch": int(epoch_idx),
                "objective": float(loss.detach().item()),
                "worst_group_loss": float(last_group_losses.max()) if last_group_losses.size > 0 else 0.0,
                "val_macro_f1": float(val_metrics["macro_f1"]),
            }
        )
        if float(val_metrics["macro_f1"]) >= float(best_val["macro_f1"]):
            best_val = val_metrics
            best_state = copy.deepcopy(out.state_dict())
            best_epoch = int(epoch_idx)

    if val_mask is not None and int(val_mask.sum().item()) > 0:
        out.load_state_dict(best_state)
    group_counts = {
        str(group_id): int((train_group_ids == int(group_id)).sum())
        for group_id in unique_groups
    }
    return out, {
        "ran": 1,
        "epochs": int(epochs),
        "group_count": int(len(unique_groups)),
        "group_counts": group_counts,
        "best_epoch": int(best_epoch),
        "best_val": best_val,
        "final_group_weights": [float(item) for item in q.tolist()],
        "final_group_losses": [float(item) for item in last_group_losses.tolist()],
        "history": history,
    }


def average_state_dicts(state_dicts: list[dict[str, torch.Tensor]], weights: list[float]) -> dict[str, torch.Tensor]:
    total_weight = max(float(sum(weights)), 1e-12)
    out: dict[str, torch.Tensor] = {}
    template = state_dicts[0]
    for key in template:
        accum = None
        for state, weight in zip(state_dicts, weights):
            tensor = state[key].detach().cpu().float() * float(weight)
            accum = tensor if accum is None else accum + tensor
        out[key] = (accum / total_weight).to(dtype=template[key].dtype)
    return out


def evaluate_known_split(
    model: GraphSAGEClassifier,
    *,
    x: torch.Tensor,
    edge_index: torch.Tensor,
    labels: torch.Tensor,
    mask: torch.Tensor,
    num_classes: int,
) -> dict[str, float]:
    if int(mask.sum().item()) <= 0:
        return {"loss": 0.0, "accuracy": 0.0, "macro_f1": 0.0}
    model.eval()
    with torch.no_grad():
        logits = model(x, edge_index)
        loss = F.cross_entropy(logits[mask], labels[mask], weight=build_class_weights(labels, mask, num_classes))
        pred = torch.argmax(logits[mask], dim=1)
    y_true = labels[mask].detach().cpu().numpy()
    y_pred = pred.detach().cpu().numpy()
    accuracy = float(np.mean(y_true == y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    return {"loss": float(loss.item()), "accuracy": accuracy, "macro_f1": macro_f1}


def uniform_confidence_loss(logits: torch.Tensor) -> torch.Tensor:
    if int(logits.shape[0]) <= 0:
        return logits.new_tensor(0.0)
    return -F.log_softmax(logits, dim=1).mean()


def infer_logits_embeddings(
    model: GraphSAGEClassifier,
    *,
    x: torch.Tensor,
    edge_index: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    model.eval()
    with torch.no_grad():
        logits, embeddings = model(x, edge_index, return_embeddings=True)
    return logits.detach().cpu(), embeddings.detach().cpu()


def _prototype_bank_pairwise_similarity(
    *,
    embeddings: torch.Tensor,
    sample_labels: torch.Tensor,
    prototype_bank: torch.Tensor,
    prototype_labels: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    normalized_embeddings = F.normalize(embeddings, dim=1)
    normalized_bank = F.normalize(prototype_bank.to(normalized_embeddings.device).float(), dim=1)
    bank_labels = prototype_labels.to(normalized_embeddings.device).long()
    label_mask = sample_labels.long().view(-1, 1) == bank_labels.view(1, -1)
    similarities = normalized_embeddings @ normalized_bank.T
    positive_sim = similarities.masked_fill(~label_mask, float("-inf")).max(dim=1).values
    negative_sim = similarities.masked_fill(label_mask, float("-inf")).max(dim=1).values
    negative_sim = torch.where(torch.isfinite(negative_sim), negative_sim, torch.full_like(negative_sim, -1.0))
    return positive_sim, negative_sim, similarities


def adapt_with_target_confidence(
    model: GraphSAGEClassifier,
    *,
    source_x: torch.Tensor,
    source_edge_index: torch.Tensor,
    source_labels: torch.Tensor,
    source_train_mask: torch.Tensor,
    target_x: torch.Tensor,
    target_edge_index: torch.Tensor,
    pseudo_labels: torch.Tensor,
    pseudo_mask: torch.Tensor,
    uncertainty_mask: torch.Tensor,
    num_classes: int,
    epochs: int,
    lr: float,
    source_weight: float = 1.0,
    pseudo_weight: float = 0.5,
    uncertainty_weight: float = 0.05,
    edge_dropout_prob: float = 0.0,
    pseudo_soft_targets: torch.Tensor | None = None,
    pseudo_sample_weights: torch.Tensor | None = None,
    source_prototypes: torch.Tensor | None = None,
    source_prototype_bank: torch.Tensor | None = None,
    source_prototype_labels: torch.Tensor | None = None,
    prototype_weight: float = 0.0,
    prototype_nonbenign_only: bool = True,
    prototype_margin_weight: float = 0.0,
    prototype_margin_value: float = 0.15,
    prototype_margin_nonbenign_only: bool = True,
    uncertainty_repulsion_weight: float = 0.0,
    uncertainty_repulsion_margin: float = 0.2,
) -> tuple[GraphSAGEClassifier, dict[str, float | int]]:
    out = copy.deepcopy(model)
    if int(epochs) <= 0 or (int(pseudo_mask.sum().item()) <= 0 and int(uncertainty_mask.sum().item()) <= 0):
        return out, {
            "epochs": int(max(epochs, 0)),
            "pseudo_nodes": int(pseudo_mask.sum().item()),
            "uncertainty_nodes": int(uncertainty_mask.sum().item()),
            "source_weight": float(source_weight),
            "pseudo_weight": float(pseudo_weight),
            "uncertainty_weight": float(uncertainty_weight),
            "prototype_weight": float(prototype_weight),
            "prototype_margin_weight": float(prototype_margin_weight),
            "prototype_margin_value": float(prototype_margin_value),
            "uncertainty_repulsion_weight": float(uncertainty_repulsion_weight),
            "uncertainty_repulsion_margin": float(uncertainty_repulsion_margin),
            "prototype_bank_size": 0,
            "ran": 0,
        }

    out.train()
    optimizer = torch.optim.Adam(out.parameters(), lr=float(lr))
    source_class_weights = build_class_weights(labels=source_labels, mask=source_train_mask, num_classes=num_classes)
    prototype_bank = None
    prototype_bank_labels = None
    if source_prototype_bank is not None and source_prototype_labels is not None:
        prototype_bank = source_prototype_bank.detach().cpu()
        prototype_bank_labels = source_prototype_labels.detach().cpu().long()
    elif source_prototypes is not None:
        prototype_bank = source_prototypes.detach().cpu()
        prototype_bank_labels = torch.arange(int(source_prototypes.shape[0]), dtype=torch.long)
    last_source_loss = 0.0
    last_pseudo_loss = 0.0
    last_uncertainty_loss = 0.0
    last_prototype_loss = 0.0
    last_prototype_margin_loss = 0.0
    last_uncertainty_repulsion_loss = 0.0
    for _ in range(int(epochs)):
        optimizer.zero_grad()
        src_edge = source_edge_index
        tgt_edge = target_edge_index
        drop_prob = min(max(float(edge_dropout_prob), 0.0), 0.95)
        if drop_prob > 0.0:
            if int(source_edge_index.shape[1]) > 1:
                keep_src = torch.rand(int(source_edge_index.shape[1])) >= drop_prob
                if int(keep_src.sum().item()) <= 0:
                    keep_src[0] = True
                src_edge = source_edge_index[:, keep_src]
            if int(target_edge_index.shape[1]) > 1:
                keep_tgt = torch.rand(int(target_edge_index.shape[1])) >= drop_prob
                if int(keep_tgt.sum().item()) <= 0:
                    keep_tgt[0] = True
                tgt_edge = target_edge_index[:, keep_tgt]

        src_logits = out(source_x, src_edge)
        loss = float(source_weight) * F.cross_entropy(
            src_logits[source_train_mask],
            source_labels[source_train_mask],
            weight=source_class_weights,
        )
        last_source_loss = float(loss.detach().item())

        tgt_logits, tgt_embeddings = out(target_x, tgt_edge, return_embeddings=True)
        if int(pseudo_mask.sum().item()) > 0:
            if pseudo_soft_targets is not None:
                pseudo_log_probs = F.log_softmax(tgt_logits[pseudo_mask], dim=1)
                soft_targets = pseudo_soft_targets[pseudo_mask].to(pseudo_log_probs.device).float()
                per_sample_pseudo = -(soft_targets * pseudo_log_probs).sum(dim=1)
            else:
                per_sample_pseudo = F.cross_entropy(
                    tgt_logits[pseudo_mask],
                    pseudo_labels[pseudo_mask],
                    reduction="none",
                )
            if pseudo_sample_weights is not None:
                sample_weights = pseudo_sample_weights[pseudo_mask].to(per_sample_pseudo.device).float()
                weight_denom = sample_weights.sum().clamp_min(1e-6)
                pseudo_loss = (per_sample_pseudo * sample_weights).sum() / weight_denom
            else:
                pseudo_loss = per_sample_pseudo.mean()
            loss = loss + float(pseudo_weight) * pseudo_loss
            last_pseudo_loss = float(pseudo_loss.detach().item())
        else:
            last_pseudo_loss = 0.0
        if float(prototype_weight) > 0.0 and prototype_bank is not None and prototype_bank_labels is not None:
            prototype_mask = pseudo_mask.clone()
            if bool(prototype_nonbenign_only):
                prototype_mask &= pseudo_labels != 0
            if int(prototype_mask.sum().item()) > 0:
                positive_sim, _, _ = _prototype_bank_pairwise_similarity(
                    embeddings=tgt_embeddings[prototype_mask],
                    sample_labels=pseudo_labels[prototype_mask],
                    prototype_bank=prototype_bank,
                    prototype_labels=prototype_bank_labels,
                )
                prototype_loss_vec = 1.0 - positive_sim
                if pseudo_sample_weights is not None:
                    proto_weights = pseudo_sample_weights[prototype_mask].to(prototype_loss_vec.device).float()
                    proto_denom = proto_weights.sum().clamp_min(1e-6)
                    prototype_loss = (prototype_loss_vec * proto_weights).sum() / proto_denom
                else:
                    prototype_loss = prototype_loss_vec.mean()
                loss = loss + float(prototype_weight) * prototype_loss
                last_prototype_loss = float(prototype_loss.detach().item())
            else:
                last_prototype_loss = 0.0
        else:
            last_prototype_loss = 0.0
        if float(prototype_margin_weight) > 0.0 and prototype_bank is not None and prototype_bank_labels is not None:
            margin_mask = pseudo_mask.clone()
            if bool(prototype_margin_nonbenign_only):
                margin_mask &= pseudo_labels != 0
            if int(margin_mask.sum().item()) > 0:
                positive_sim, hardest_negative, _ = _prototype_bank_pairwise_similarity(
                    embeddings=tgt_embeddings[margin_mask],
                    sample_labels=pseudo_labels[margin_mask],
                    prototype_bank=prototype_bank,
                    prototype_labels=prototype_bank_labels,
                )
                prototype_margin_loss_vec = F.relu(
                    float(prototype_margin_value) - (positive_sim - hardest_negative)
                )
                if pseudo_sample_weights is not None:
                    margin_weights = pseudo_sample_weights[margin_mask].to(prototype_margin_loss_vec.device).float()
                    margin_denom = margin_weights.sum().clamp_min(1e-6)
                    prototype_margin_loss = (prototype_margin_loss_vec * margin_weights).sum() / margin_denom
                else:
                    prototype_margin_loss = prototype_margin_loss_vec.mean()
                loss = loss + float(prototype_margin_weight) * prototype_margin_loss
                last_prototype_margin_loss = float(prototype_margin_loss.detach().item())
            else:
                last_prototype_margin_loss = 0.0
        else:
            last_prototype_margin_loss = 0.0
        if int(uncertainty_mask.sum().item()) > 0:
            unc_loss = uniform_confidence_loss(tgt_logits[uncertainty_mask])
            loss = loss + float(uncertainty_weight) * unc_loss
            last_uncertainty_loss = float(unc_loss.detach().item())
            if float(uncertainty_repulsion_weight) > 0.0 and prototype_bank is not None:
                uncertainty_embeddings = F.normalize(tgt_embeddings[uncertainty_mask], dim=1)
                normalized_prototypes = F.normalize(
                    prototype_bank.to(uncertainty_embeddings.device).float(),
                    dim=1,
                )
                max_similarity = (uncertainty_embeddings @ normalized_prototypes.T).max(dim=1).values
                uncertainty_repulsion_loss = F.relu(max_similarity - float(uncertainty_repulsion_margin)).mean()
                loss = loss + float(uncertainty_repulsion_weight) * uncertainty_repulsion_loss
                last_uncertainty_repulsion_loss = float(uncertainty_repulsion_loss.detach().item())
            else:
                last_uncertainty_repulsion_loss = 0.0
        else:
            last_uncertainty_loss = 0.0
            last_uncertainty_repulsion_loss = 0.0

        loss.backward()
        optimizer.step()

    return out, {
        "epochs": int(epochs),
        "pseudo_nodes": int(pseudo_mask.sum().item()),
        "uncertainty_nodes": int(uncertainty_mask.sum().item()),
        "source_weight": float(source_weight),
        "pseudo_weight": float(pseudo_weight),
        "uncertainty_weight": float(uncertainty_weight),
        "prototype_weight": float(prototype_weight),
        "prototype_margin_weight": float(prototype_margin_weight),
        "prototype_margin_value": float(prototype_margin_value),
        "uncertainty_repulsion_weight": float(uncertainty_repulsion_weight),
        "uncertainty_repulsion_margin": float(uncertainty_repulsion_margin),
        "last_source_loss": float(last_source_loss),
        "last_pseudo_loss": float(last_pseudo_loss),
        "last_uncertainty_loss": float(last_uncertainty_loss),
        "last_prototype_loss": float(last_prototype_loss),
        "last_prototype_margin_loss": float(last_prototype_margin_loss),
        "last_uncertainty_repulsion_loss": float(last_uncertainty_repulsion_loss),
        "soft_targets_enabled": int(pseudo_soft_targets is not None),
        "weighted_pseudo_enabled": int(pseudo_sample_weights is not None),
        "prototype_bank_size": int(prototype_bank.shape[0]) if prototype_bank is not None else 0,
        "prototype_nodes": int(((pseudo_mask & (pseudo_labels != 0)) if prototype_nonbenign_only else pseudo_mask).sum().item()),
        "prototype_margin_nodes": int(((pseudo_mask & (pseudo_labels != 0)) if prototype_margin_nonbenign_only else pseudo_mask).sum().item()),
        "ran": 1,
    }


def run_fedavg_training(
    *,
    source_graph,
    source_labels: torch.Tensor,
    train_mask: torch.Tensor,
    val_mask: torch.Tensor,
    client_views: list[dict[str, Any]],
    num_classes: int,
    seed: int,
    hidden_dim: int,
    dropout: float,
    global_warmup_epochs: int,
    rounds: int,
    local_epochs: int,
    lr: float,
    edge_dropout_prob: float = 0.0,
    center_loss_weight: float = 0.0,
    center_margin_weight: float = 0.0,
    center_margin_value: float = 0.15,
) -> tuple[GraphSAGEClassifier, dict[str, Any]]:
    set_random_seed(seed)
    model = GraphSAGEClassifier(
        in_dim=int(source_graph.x_norm.shape[1]),
        hidden_dim=int(hidden_dim),
        out_dim=int(num_classes),
        dropout=float(dropout),
    )
    x = source_graph.x_norm.float()
    edge_index = source_graph.edge_index.long()
    if int(train_mask.sum().item()) > 0 and int(global_warmup_epochs) > 0:
        model = train_supervised(
            model,
            x=x,
            edge_index=edge_index,
            labels=source_labels,
            mask=train_mask,
            epochs=global_warmup_epochs,
            lr=lr,
            num_classes=num_classes,
            edge_dropout_prob=edge_dropout_prob,
            center_loss_weight=center_loss_weight,
            center_margin_weight=center_margin_weight,
            center_margin_value=center_margin_value,
        )

    best_state = copy.deepcopy(model.state_dict())
    best_val = evaluate_known_split(
        model,
        x=x,
        edge_index=edge_index,
        labels=source_labels,
        mask=val_mask,
        num_classes=num_classes,
    )
    best_round = 0
    history: list[dict[str, float | int]] = [{"round": 0, **best_val}]

    for round_id in range(1, int(rounds) + 1):
        local_states: list[dict[str, torch.Tensor]] = []
        local_weights: list[float] = []
        for view in client_views:
            if int(view["train_nodes"]) <= 0:
                continue
            local_model = train_supervised(
                model,
                x=view["x"],
                edge_index=view["edge_index"],
                labels=view["labels"],
                mask=view["train_mask"],
                epochs=local_epochs,
                lr=lr,
                num_classes=num_classes,
                edge_dropout_prob=edge_dropout_prob,
                center_loss_weight=center_loss_weight,
                center_margin_weight=center_margin_weight,
                center_margin_value=center_margin_value,
            )
            local_states.append(copy.deepcopy(local_model.state_dict()))
            local_weights.append(float(view["train_nodes"]))
        if not local_states:
            break
        model.load_state_dict(average_state_dicts(local_states, local_weights))
        val_metrics = evaluate_known_split(
            model,
            x=x,
            edge_index=edge_index,
            labels=source_labels,
            mask=val_mask,
            num_classes=num_classes,
        )
        history.append({"round": int(round_id), **val_metrics})
        if float(val_metrics["macro_f1"]) >= float(best_val["macro_f1"]):
            best_val = val_metrics
            best_state = copy.deepcopy(model.state_dict())
            best_round = int(round_id)

    model.load_state_dict(best_state)
    active_clients = int(sum(1 for view in client_views if int(view["train_nodes"]) > 0))
    return model, {
        "best_round": best_round,
        "best_val": best_val,
        "history": history,
        "rounds_completed": max(len(history) - 1, 0),
        "active_clients": active_clients,
    }
