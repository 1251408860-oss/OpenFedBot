from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression


@dataclass
class DeferralCalibrator:
    temperature: float
    aps_quantile: float
    prototype_threshold: float
    prototype_thresholds: np.ndarray
    multi_proto_distance_threshold: float
    multi_proto_distance_thresholds: np.ndarray
    multi_proto_margin_threshold: float
    multi_proto_margin_thresholds: np.ndarray
    multi_proto_distance_scale: float
    multi_proto_margin_scale: float
    knn_distance_threshold: float
    knn_distance_thresholds: np.ndarray
    knn_distance_scale: float
    knn_k: int
    trust_threshold: float
    trust_thresholds: np.ndarray
    trust_score_scale: float
    trust_k: int
    confidence_threshold: float
    energy_threshold: float
    coverage_target: float
    alpha: float
    cpd_threshold: float
    cpd_risk_target: float
    cpd_conf_scale: float
    cpd_proto_scale: float
    cpd_val_coverage: float
    cpd_val_risk: float
    ova_score_scale: float
    soft_consensus_threshold: float
    soft_consensus_risk_target: float
    soft_consensus_val_coverage: float
    soft_consensus_val_risk: float
    trust_consensus_threshold: float
    trust_consensus_risk_target: float
    trust_consensus_val_coverage: float
    trust_consensus_val_risk: float
    benign_reclaim_threshold: float
    benign_reclaim_risk_target: float
    benign_reclaim_val_coverage: float
    benign_reclaim_val_risk: float
    nonbenign_bridge_threshold: float
    nonbenign_bridge_risk_target: float
    nonbenign_bridge_val_coverage: float
    nonbenign_bridge_val_risk: float
    prototypes: torch.Tensor
    multi_prototypes: torch.Tensor
    multi_prototype_labels: torch.Tensor
    support_embeddings: torch.Tensor
    support_labels: torch.Tensor


@dataclass
class OVAModel:
    weights: np.ndarray
    bias: np.ndarray


@dataclass
class OVAGate:
    threshold: float
    weights: np.ndarray
    bias: np.ndarray


@dataclass
class ReviewSelector:
    threshold: float
    weights: np.ndarray
    bias: float
    feature_mean: np.ndarray
    feature_scale: np.ndarray
    benign_target: float
    mode: str = "logreg"
    benign_score_threshold: float = 1.0


def fit_temperature(logits: torch.Tensor, labels: torch.Tensor) -> float:
    logits = logits.detach().float()
    labels = labels.detach().long()
    log_temperature = torch.nn.Parameter(torch.zeros(1))
    optimizer = torch.optim.LBFGS([log_temperature], lr=0.2, max_iter=50, line_search_fn="strong_wolfe")

    def closure() -> torch.Tensor:
        optimizer.zero_grad()
        temperature = torch.exp(log_temperature).clamp(min=1e-3, max=100.0)
        loss = F.cross_entropy(logits / temperature, labels)
        loss.backward()
        return loss

    optimizer.step(closure)
    return float(torch.exp(log_temperature).clamp(min=1e-3, max=100.0).item())


def apply_temperature(logits: torch.Tensor, temperature: float) -> torch.Tensor:
    return logits / max(float(temperature), 1e-6)


def aps_true_class_scores(probs: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
    sorted_probs, sorted_idx = torch.sort(probs, dim=1, descending=True)
    cumulative = torch.cumsum(sorted_probs, dim=1)
    inverse_rank = torch.empty_like(sorted_idx)
    ranks = torch.arange(probs.shape[1], device=probs.device).view(1, -1).expand_as(sorted_idx)
    inverse_rank.scatter_(1, sorted_idx, ranks)
    true_rank = inverse_rank[torch.arange(labels.shape[0], device=labels.device), labels]
    return cumulative[torch.arange(labels.shape[0], device=labels.device), true_rank]


def conformal_quantile(scores: torch.Tensor, alpha: float) -> float:
    arr = np.sort(scores.detach().cpu().numpy().astype(np.float64, copy=False))
    n = len(arr)
    level = np.ceil((n + 1) * (1.0 - float(alpha))) / max(n, 1)
    level = min(max(level, 0.0), 1.0)
    return float(np.quantile(arr, level, method="higher"))


def aps_prediction_sets(probs: torch.Tensor, quantile: float) -> torch.Tensor:
    sorted_probs, sorted_idx = torch.sort(probs, dim=1, descending=True)
    cumulative = torch.cumsum(sorted_probs, dim=1)
    include_sorted = cumulative <= float(quantile)
    first_over = torch.argmax((cumulative >= float(quantile)).long(), dim=1)
    include_sorted[torch.arange(probs.shape[0]), first_over] = True
    include = torch.zeros_like(include_sorted, dtype=torch.bool)
    include.scatter_(1, sorted_idx, include_sorted)
    return include


def build_class_prototypes(
    embeddings: torch.Tensor,
    labels: torch.Tensor,
    mask: torch.Tensor,
    num_classes: int,
) -> torch.Tensor:
    normalized = F.normalize(embeddings.detach().float(), dim=1)
    prototypes = []
    for class_id in range(int(num_classes)):
        class_mask = mask & (labels == int(class_id))
        class_embeddings = normalized[class_mask]
        if class_embeddings.shape[0] <= 0:
            raise RuntimeError(f"missing calibration embeddings for class {class_id}")
        proto = class_embeddings.mean(dim=0, keepdim=True)
        proto = F.normalize(proto, dim=1)
        prototypes.append(proto)
    return torch.cat(prototypes, dim=0)


def build_multi_prototype_bank(
    embeddings: torch.Tensor,
    labels: torch.Tensor,
    mask: torch.Tensor,
    num_classes: int,
    *,
    max_prototypes_per_class: int = 1,
    min_points_per_proto: int = 16,
    random_seed: int = 0,
) -> tuple[torch.Tensor, torch.Tensor]:
    normalized = F.normalize(embeddings.detach().float(), dim=1)
    prototypes: list[torch.Tensor] = []
    prototype_labels: list[torch.Tensor] = []
    max_proto = max(int(max_prototypes_per_class), 1)
    min_points = max(int(min_points_per_proto), 1)
    for class_id in range(int(num_classes)):
        class_mask = mask & (labels == int(class_id))
        class_embeddings = normalized[class_mask]
        class_count = int(class_embeddings.shape[0])
        if class_count <= 0:
            raise RuntimeError(f"missing calibration embeddings for class {class_id}")

        cluster_count = 1
        if max_proto > 1 and class_count > 1:
            suggested = int(np.ceil(class_count / float(min_points)))
            cluster_count = min(max_proto, max(suggested, 1), class_count)

        if cluster_count <= 1:
            class_prototypes = F.normalize(class_embeddings.mean(dim=0, keepdim=True), dim=1)
        else:
            class_np = class_embeddings.detach().cpu().numpy().astype(np.float64, copy=False)
            model = KMeans(
                n_clusters=int(cluster_count),
                n_init=10,
                random_state=int(random_seed) + int(class_id),
            )
            assignments = model.fit_predict(class_np)
            centers: list[torch.Tensor] = []
            for cluster_id in range(int(cluster_count)):
                cluster_idx = np.flatnonzero(assignments == int(cluster_id))
                if cluster_idx.size <= 0:
                    continue
                cluster_tensor = class_embeddings[torch.as_tensor(cluster_idx, dtype=torch.long)]
                center = F.normalize(cluster_tensor.mean(dim=0, keepdim=True), dim=1)
                centers.append(center)
            class_prototypes = (
                torch.cat(centers, dim=0)
                if centers
                else F.normalize(class_embeddings.mean(dim=0, keepdim=True), dim=1)
            )

        prototypes.append(class_prototypes)
        prototype_labels.append(torch.full((int(class_prototypes.shape[0]),), int(class_id), dtype=torch.long))

    return torch.cat(prototypes, dim=0), torch.cat(prototype_labels, dim=0)


def prototype_distances(embeddings: torch.Tensor, prototypes: torch.Tensor) -> torch.Tensor:
    normalized = F.normalize(embeddings.detach().float(), dim=1)
    proto_norm = F.normalize(prototypes.detach().float(), dim=1)
    similarities = normalized @ proto_norm.T
    return 1.0 - similarities


def classwise_knn_distances(
    *,
    embeddings: torch.Tensor,
    support_embeddings: torch.Tensor,
    support_labels: torch.Tensor,
    pred: np.ndarray,
    k: int,
) -> np.ndarray:
    normalized_queries = F.normalize(embeddings.detach().float(), dim=1).detach().cpu()
    normalized_support = F.normalize(support_embeddings.detach().float(), dim=1).detach().cpu()
    support_label_np = support_labels.detach().cpu().numpy().astype(np.int64, copy=False)
    pred_np = np.asarray(pred, dtype=np.int64, copy=False)
    out = np.full((int(pred_np.shape[0]),), np.inf, dtype=np.float64)
    max_k = max(int(k), 1)
    for class_id in np.unique(pred_np).tolist():
        query_idx = np.flatnonzero(pred_np == int(class_id))
        support_idx = np.flatnonzero(support_label_np == int(class_id))
        if query_idx.size <= 0 or support_idx.size <= 0:
            continue
        query_tensor = normalized_queries[torch.as_tensor(query_idx, dtype=torch.long)]
        support_tensor = normalized_support[torch.as_tensor(support_idx, dtype=torch.long)]
        similarities = query_tensor @ support_tensor.T
        k_eff = min(max_k, int(support_tensor.shape[0]))
        topk = torch.topk(similarities, k=k_eff, dim=1, largest=True).values
        distances = 1.0 - topk.mean(dim=1)
        out[query_idx] = distances.detach().cpu().numpy().astype(np.float64, copy=False)
    return out


def classwise_trust_scores(
    *,
    embeddings: torch.Tensor,
    support_embeddings: torch.Tensor,
    support_labels: torch.Tensor,
    pred: np.ndarray,
    k: int,
) -> np.ndarray:
    normalized_queries = F.normalize(embeddings.detach().float(), dim=1).detach().cpu()
    normalized_support = F.normalize(support_embeddings.detach().float(), dim=1).detach().cpu()
    support_label_np = support_labels.detach().cpu().numpy().astype(np.int64, copy=False)
    pred_np = np.asarray(pred, dtype=np.int64, copy=False)
    out = np.full((int(pred_np.shape[0]),), -np.inf, dtype=np.float64)
    max_k = max(int(k), 1)
    eps = 1e-6
    unique_labels = sorted(set(int(item) for item in support_label_np.tolist()))
    for class_id in np.unique(pred_np).tolist():
        query_idx = np.flatnonzero(pred_np == int(class_id))
        own_idx = np.flatnonzero(support_label_np == int(class_id))
        other_labels = [label for label in unique_labels if label != int(class_id)]
        if query_idx.size <= 0 or own_idx.size <= 0 or not other_labels:
            continue
        query_tensor = normalized_queries[torch.as_tensor(query_idx, dtype=torch.long)]
        own_tensor = normalized_support[torch.as_tensor(own_idx, dtype=torch.long)]
        own_k = min(max_k, int(own_tensor.shape[0]))
        own_sim = query_tensor @ own_tensor.T
        own_dist = 1.0 - torch.topk(own_sim, k=own_k, dim=1, largest=True).values.mean(dim=1)
        competitor_distances: list[torch.Tensor] = []
        for other_label in other_labels:
            other_idx = np.flatnonzero(support_label_np == int(other_label))
            if other_idx.size <= 0:
                continue
            other_tensor = normalized_support[torch.as_tensor(other_idx, dtype=torch.long)]
            other_k = min(max_k, int(other_tensor.shape[0]))
            other_sim = query_tensor @ other_tensor.T
            other_dist = 1.0 - torch.topk(other_sim, k=other_k, dim=1, largest=True).values.mean(dim=1)
            competitor_distances.append(other_dist.unsqueeze(1))
        if not competitor_distances:
            continue
        nearest_other_dist = torch.cat(competitor_distances, dim=1).min(dim=1).values
        trust_score = torch.log(nearest_other_dist + eps) - torch.log(own_dist + eps)
        out[query_idx] = trust_score.detach().cpu().numpy().astype(np.float64, copy=False)
    return out


def multiproto_distance_features(
    *,
    embeddings: torch.Tensor,
    prototypes: torch.Tensor,
    prototype_labels: torch.Tensor,
    pred: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    normalized = F.normalize(embeddings.detach().float(), dim=1)
    proto_norm = F.normalize(prototypes.detach().float(), dim=1)
    distances = (1.0 - normalized @ proto_norm.T).detach().cpu()
    pred_np = np.asarray(pred, dtype=np.int64, copy=False)
    proto_label_np = prototype_labels.detach().cpu().numpy().astype(np.int64, copy=False)
    same_distance = np.full((int(pred_np.shape[0]),), np.inf, dtype=np.float64)
    other_distance = np.full((int(pred_np.shape[0]),), np.inf, dtype=np.float64)
    margin = np.full((int(pred_np.shape[0]),), -np.inf, dtype=np.float64)
    nearest_same_index = np.full((int(pred_np.shape[0]),), -1, dtype=np.int64)
    unique_pred = sorted(set(int(item) for item in pred_np.tolist()))
    for class_id in unique_pred:
        query_idx = np.flatnonzero(pred_np == int(class_id))
        if query_idx.size <= 0:
            continue
        same_idx = np.flatnonzero(proto_label_np == int(class_id))
        other_idx = np.flatnonzero(proto_label_np != int(class_id))
        query_distances = distances[torch.as_tensor(query_idx, dtype=torch.long)]
        if same_idx.size > 0:
            same_distances = query_distances[:, torch.as_tensor(same_idx, dtype=torch.long)]
            min_same = torch.min(same_distances, dim=1)
            same_distance[query_idx] = min_same.values.detach().cpu().numpy().astype(np.float64, copy=False)
            nearest_same_index[query_idx] = same_idx[min_same.indices.detach().cpu().numpy().astype(np.int64, copy=False)]
        if other_idx.size > 0:
            other_distances = query_distances[:, torch.as_tensor(other_idx, dtype=torch.long)]
            min_other = torch.min(other_distances, dim=1).values
            other_distance[query_idx] = min_other.detach().cpu().numpy().astype(np.float64, copy=False)
        margin[query_idx] = other_distance[query_idx] - same_distance[query_idx]
    return same_distance, other_distance, margin, nearest_same_index


def adapt_prototypes_with_target(
    *,
    embeddings: torch.Tensor,
    pred: np.ndarray,
    accept: np.ndarray,
    prototypes: torch.Tensor,
    momentum: float,
) -> torch.Tensor:
    weight = min(max(float(momentum), 0.0), 1.0)
    if weight <= 0.0:
        return prototypes.detach().cpu()
    normalized = F.normalize(embeddings.detach().float(), dim=1).detach().cpu()
    out = F.normalize(prototypes.detach().cpu().float(), dim=1)
    pred_np = np.asarray(pred, dtype=np.int64)
    accept_np = np.asarray(accept, dtype=bool)
    for class_id in range(int(out.shape[0])):
        class_idx = np.flatnonzero(accept_np & (pred_np == int(class_id)))
        if class_idx.size <= 0:
            continue
        target_center = normalized[torch.as_tensor(class_idx, dtype=torch.long)].mean(dim=0, keepdim=True)
        target_center = F.normalize(target_center, dim=1)
        mixed = F.normalize((1.0 - weight) * out[class_id : class_id + 1] + weight * target_center, dim=1)
        out[class_id : class_id + 1] = mixed
    return out


def _score_scale(values: np.ndarray) -> float:
    arr = np.asarray(values, dtype=np.float64)
    if arr.size <= 1:
        return 1.0
    q25, q75 = np.quantile(arr, [0.25, 0.75])
    scale = float(q75 - q25)
    if scale <= 1e-6:
        scale = float(arr.std(ddof=0))
    return max(scale, 1e-6)


def _classwise_quantile_thresholds(
    *,
    values: np.ndarray,
    pred: np.ndarray,
    accept: np.ndarray,
    num_classes: int,
    quantile: float,
    min_count: int,
    default: np.ndarray | float,
    use_upper: bool,
) -> np.ndarray:
    out = np.asarray(default, dtype=np.float64).copy()
    values_np = np.asarray(values, dtype=np.float64, copy=False)
    pred_np = np.asarray(pred, dtype=np.int64, copy=False)
    accept_np = np.asarray(accept, dtype=bool, copy=False)
    q = min(max(float(quantile), 0.0), 1.0)
    for class_id in range(int(num_classes)):
        class_mask = accept_np & (pred_np == int(class_id))
        if int(class_mask.sum()) < int(min_count):
            continue
        out[int(class_id)] = float(np.quantile(values_np[class_mask], q, method="higher" if use_upper else "lower"))
    return out


def _select_risk_bounded_threshold(
    *,
    scores: np.ndarray,
    errors: np.ndarray,
    risk_target: float,
    coverage_cap: float,
    total_count: int | None = None,
) -> tuple[float, float, float]:
    order = np.argsort(-scores, kind="stable")
    ordered_scores = scores[order]
    ordered_errors = errors[order].astype(np.float64, copy=False)
    cumulative_error = np.cumsum(ordered_errors)
    ranks = np.arange(1, ordered_scores.shape[0] + 1, dtype=np.float64)
    risk = cumulative_error / ranks
    denom = max(int(total_count) if total_count is not None else len(order), 1)
    coverage = ranks / float(denom)
    valid = np.flatnonzero((risk <= float(risk_target)) & (coverage <= float(coverage_cap)))
    if valid.size > 0:
        idx = int(valid[-1])
        threshold = float(ordered_scores[idx])
        realized_coverage = float((idx + 1) / max(len(order), 1))
        realized_risk = float(risk[idx])
        return threshold, realized_coverage, realized_risk

    best_idx = int(np.argmin(risk))
    threshold = float(ordered_scores[best_idx])
    realized_coverage = float((best_idx + 1) / max(len(order), 1))
    realized_risk = float(risk[best_idx])
    return threshold, realized_coverage, realized_risk


def _select_masked_risk_bounded_threshold(
    *,
    scores: np.ndarray,
    errors: np.ndarray,
    mask: np.ndarray,
    risk_target: float,
    coverage_cap: float,
    total_count: int,
) -> tuple[float, float, float]:
    masked = np.asarray(mask, dtype=bool)
    if int(masked.sum()) <= 0:
        return float("inf"), 0.0, 1.0
    return _select_risk_bounded_threshold(
        scores=np.asarray(scores, dtype=np.float64, copy=False)[masked],
        errors=np.asarray(errors, dtype=bool, copy=False)[masked],
        risk_target=float(risk_target),
        coverage_cap=float(coverage_cap),
        total_count=int(total_count),
    )


def subsample_calibration_bank(
    *,
    val_logits: torch.Tensor,
    val_embeddings: torch.Tensor,
    val_labels: torch.Tensor,
    fraction: float,
    seed: int,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, dict[str, float | int]]:
    bank_fraction = min(max(float(fraction), 0.0), 1.0)
    total = int(val_labels.shape[0])
    if total <= 0:
        raise RuntimeError("empty calibration bank")
    if bank_fraction >= 1.0:
        return (
            val_logits,
            val_embeddings,
            val_labels,
            {
                "bank_fraction_requested": bank_fraction,
                "bank_fraction_realized": 1.0,
                "bank_size": total,
                "bank_size_full": total,
            },
        )

    rng = np.random.default_rng(int(seed))
    labels_np = val_labels.detach().cpu().numpy().astype(np.int64, copy=False)
    selected: list[int] = []
    for class_id in sorted(np.unique(labels_np).tolist()):
        class_idx = np.flatnonzero(labels_np == int(class_id))
        if class_idx.size <= 0:
            continue
        take = max(1, int(np.ceil(class_idx.size * bank_fraction)))
        if take >= class_idx.size:
            chosen = class_idx
        else:
            chosen = np.sort(rng.choice(class_idx, size=take, replace=False))
        selected.extend(int(idx) for idx in chosen.tolist())

    if not selected:
        selected = list(range(total))
    unique_idx = np.asarray(sorted(set(selected)), dtype=np.int64)
    torch_idx = torch.as_tensor(unique_idx, dtype=torch.long)
    realized = float(unique_idx.shape[0] / max(total, 1))
    return (
        val_logits[torch_idx],
        val_embeddings[torch_idx],
        val_labels[torch_idx],
        {
            "bank_fraction_requested": bank_fraction,
            "bank_fraction_realized": realized,
            "bank_size": int(unique_idx.shape[0]),
            "bank_size_full": total,
        },
    )


def _normalized_numpy_embeddings(embeddings: torch.Tensor) -> np.ndarray:
    normalized = F.normalize(embeddings.detach().float(), dim=1)
    return normalized.detach().cpu().numpy().astype(np.float64, copy=False)


def fit_ova_model(
    *,
    train_embeddings: torch.Tensor,
    train_labels: torch.Tensor,
    train_mask: torch.Tensor,
    num_classes: int,
) -> OVAModel:
    x_train = _normalized_numpy_embeddings(train_embeddings[train_mask])
    y_train = train_labels[train_mask].detach().cpu().numpy().astype(np.int64, copy=False)
    weights: list[np.ndarray] = []
    bias: list[float] = []
    for class_id in range(int(num_classes)):
        target = (y_train == int(class_id)).astype(np.int64, copy=False)
        model = LogisticRegression(
            solver="lbfgs",
            max_iter=400,
            class_weight="balanced",
            random_state=0,
        )
        model.fit(x_train, target)
        weights.append(model.coef_[0].astype(np.float64, copy=False))
        bias.append(float(model.intercept_[0]))
    return OVAModel(
        weights=np.asarray(weights, dtype=np.float64),
        bias=np.asarray(bias, dtype=np.float64),
    )


def ova_probabilities(embeddings: torch.Tensor, ova_model: OVAModel | OVAGate) -> np.ndarray:
    x = _normalized_numpy_embeddings(embeddings)
    logits = x @ np.asarray(ova_model.weights, dtype=np.float64).T + np.asarray(ova_model.bias, dtype=np.float64)
    logits = np.clip(logits, -50.0, 50.0)
    return 1.0 / (1.0 + np.exp(-logits))


def calibrate_ova_gate(
    *,
    ova_model: OVAModel,
    val_embeddings: torch.Tensor,
    coverage_target: float,
) -> OVAGate:
    probs = ova_probabilities(val_embeddings, ova_model)
    max_score = np.max(probs, axis=1)
    threshold = float(np.quantile(max_score, 1.0 - float(coverage_target), method="higher"))
    return OVAGate(
        threshold=threshold,
        weights=np.asarray(ova_model.weights, dtype=np.float64),
        bias=np.asarray(ova_model.bias, dtype=np.float64),
    )


def _review_selector_feature_matrix(
    *,
    pred_np: np.ndarray,
    ova_pred: np.ndarray,
    aps_singleton: np.ndarray,
    confidence_margin: np.ndarray,
    proto_margin: np.ndarray,
    aps_margin: np.ndarray,
    ova_margin: np.ndarray,
    soft_consensus_score: np.ndarray,
    benign_reclaim_score: np.ndarray,
) -> np.ndarray:
    feature_columns = [
        np.asarray(confidence_margin, dtype=np.float64),
        np.asarray(proto_margin, dtype=np.float64),
        np.asarray(aps_margin, dtype=np.float64),
        np.asarray(ova_margin, dtype=np.float64),
        np.asarray(soft_consensus_score, dtype=np.float64),
        np.asarray(benign_reclaim_score, dtype=np.float64),
        np.asarray(aps_singleton, dtype=np.float64),
        np.asarray(pred_np == ova_pred, dtype=np.float64),
        np.asarray(pred_np == 0, dtype=np.float64),
        np.asarray(ova_pred == 0, dtype=np.float64),
        np.asarray(pred_np == 1, dtype=np.float64),
        np.asarray(pred_np == 2, dtype=np.float64),
        np.asarray(ova_pred == 1, dtype=np.float64),
        np.asarray(ova_pred == 2, dtype=np.float64),
    ]
    return np.column_stack(feature_columns).astype(np.float64, copy=False)


def review_selector_scores(features: np.ndarray, selector: ReviewSelector) -> np.ndarray:
    feats = np.asarray(features, dtype=np.float64)
    centered = (feats - selector.feature_mean) / selector.feature_scale
    logits = centered @ selector.weights + float(selector.bias)
    logits = np.clip(logits, -50.0, 50.0)
    return 1.0 / (1.0 + np.exp(-logits))


def fit_review_selector(
    *,
    val_logits: torch.Tensor,
    val_embeddings: torch.Tensor,
    val_labels: torch.Tensor,
    calibrator: DeferralCalibrator,
    ova_gate: OVAGate | None,
    benign_target: float = 0.25,
) -> tuple[ReviewSelector | None, dict[str, float | int]]:
    def _safe_ratio(num: float, den: float) -> float:
        return float(num / den) if float(den) > 0.0 else 0.0

    if ova_gate is None:
        return None, {
            "ran": 0,
            "reason": "missing_ova_gate",
        }

    calibrated_val_logits = apply_temperature(val_logits, calibrator.temperature)
    val_probs = torch.softmax(calibrated_val_logits, dim=1)
    val_pred = torch.argmax(calibrated_val_logits, dim=1)
    max_prob = torch.max(val_probs, dim=1).values
    aps_sets = aps_prediction_sets(val_probs, calibrator.aps_quantile)
    aps_singleton = (aps_sets.sum(dim=1) == 1).detach().cpu().numpy().astype(bool, copy=False)
    distances = prototype_distances(val_embeddings, calibrator.prototypes)
    pred_distance = distances[torch.arange(val_pred.shape[0]), val_pred]

    pred_np = val_pred.detach().cpu().numpy().astype(np.int64, copy=False)
    labels_np = val_labels.detach().cpu().numpy().astype(np.int64, copy=False)
    max_prob_np = max_prob.detach().cpu().numpy().astype(np.float64, copy=False)
    proto_thresholds = np.asarray(calibrator.prototype_thresholds, dtype=np.float64)
    pred_distance_np = pred_distance.detach().cpu().numpy().astype(np.float64, copy=False)
    proto_margin = proto_thresholds[pred_np] - pred_distance_np
    aps_margin = max_prob_np - float(calibrator.aps_quantile)
    confidence_margin = max_prob_np - float(calibrator.confidence_threshold)

    ova_probs = ova_probabilities(val_embeddings, ova_gate)
    ova_pred = np.argmax(ova_probs, axis=1).astype(np.int64, copy=False)
    ova_max_score = np.max(ova_probs, axis=1).astype(np.float64, copy=False)
    ova_margin = ova_max_score - float(ova_gate.threshold)
    soft_consensus_score = np.minimum.reduce(
        [
            confidence_margin / max(float(calibrator.cpd_conf_scale), 1e-6),
            proto_margin / max(float(calibrator.cpd_proto_scale), 1e-6),
            ova_margin / max(float(calibrator.ova_score_scale), 1e-6),
        ]
    )
    benign_reclaim_score = np.minimum.reduce(
        [
            confidence_margin / max(float(calibrator.cpd_conf_scale), 1e-6),
            proto_margin / max(float(calibrator.cpd_proto_scale), 1e-6),
            ova_margin / max(float(calibrator.ova_score_scale), 1e-6),
        ]
    )
    benign_reclaim_accept = (
        (pred_np == 0)
        & (ova_pred == 0)
        & (proto_margin >= 0.0)
        & (ova_margin >= 0.0)
        & (benign_reclaim_score >= float(calibrator.benign_reclaim_threshold))
    )
    auto_accept = (
        (aps_singleton)
        & (proto_margin >= 0.0)
        & (ova_margin >= 0.0)
        & (ova_pred == pred_np)
    ) | benign_reclaim_accept
    review_accept = ova_margin >= 0.0
    candidate_mask = (~auto_accept) & review_accept
    candidate_count = int(candidate_mask.sum())
    benign_total = max(int((labels_np == 0).sum()), 1)
    known_total = max(int((labels_np >= 0).sum()), 1)
    nonbenign_total = max(int((labels_np > 0).sum()), 1)
    if candidate_count < 8:
        return None, {
            "ran": 0,
            "reason": "too_few_candidates",
            "candidate_count": candidate_count,
        }

    candidate_benign = candidate_mask & (ova_pred == 0)
    benign_candidate_scores = ova_max_score[candidate_benign]
    no_benign_threshold = float(np.nextafter(float(benign_candidate_scores.max()), np.inf)) if benign_candidate_scores.size > 0 else 1.0
    selector = ReviewSelector(
        threshold=float(ova_gate.threshold),
        weights=np.zeros((0,), dtype=np.float64),
        bias=0.0,
        feature_mean=np.zeros((0,), dtype=np.float64),
        feature_scale=np.ones((0,), dtype=np.float64),
        benign_target=float(benign_target),
        mode="benign_budget",
        benign_score_threshold=no_benign_threshold,
    )
    best_threshold = float(selector.benign_score_threshold)
    best_benign_rate = 0.0
    best_correct_review_rate = 0.0
    thresholds = np.unique(benign_candidate_scores) if benign_candidate_scores.size > 0 else np.asarray([], dtype=np.float64)
    for threshold in thresholds:
        selected = candidate_mask & ((ova_pred != 0) | (ova_max_score >= float(threshold)))
        benign_rate = _safe_ratio(float((selected & (labels_np == 0)).sum()), float(benign_total))
        correct_review_rate = _safe_ratio(
            float((selected & (labels_np >= 0) & (ova_pred == labels_np)).sum()),
            float(known_total),
        )
        nonbenign_capture = _safe_ratio(
            float((selected & (labels_np > 0) & (ova_pred == labels_np)).sum()),
            float(nonbenign_total),
        )
        if benign_rate > float(benign_target) + 1e-12:
            continue
        if (correct_review_rate > best_correct_review_rate + 1e-12) or (
            abs(correct_review_rate - best_correct_review_rate) <= 1e-12 and benign_rate < best_benign_rate
        ):
            best_threshold = float(threshold)
            best_benign_rate = float(benign_rate)
            best_correct_review_rate = float(correct_review_rate)

    selector.benign_score_threshold = float(best_threshold)
    selected = candidate_mask & ((ova_pred != 0) | (ova_max_score >= selector.benign_score_threshold))
    return selector, {
        "ran": 1,
        "candidate_count": candidate_count,
        "candidate_fraction": _safe_ratio(float(candidate_count), float(labels_np.shape[0])),
        "positive_count": int((candidate_mask & (labels_np >= 0) & (ova_pred == labels_np)).sum()),
        "benign_target": float(benign_target),
        "threshold": float(selector.benign_score_threshold),
        "val_benign_review_rate": _safe_ratio(float((selected & (labels_np == 0)).sum()), float(benign_total)),
        "val_correct_review_rate": _safe_ratio(
            float((selected & (labels_np >= 0) & (ova_pred == labels_np)).sum()),
            float(known_total),
        ),
        "val_nonbenign_capture_rate": _safe_ratio(
            float((selected & (labels_np > 0) & (ova_pred == labels_np)).sum()),
            float(nonbenign_total),
        ),
    }


def fit_calibrator(
    *,
    val_logits: torch.Tensor,
    val_embeddings: torch.Tensor,
    val_labels: torch.Tensor,
    train_embeddings: torch.Tensor,
    train_labels: torch.Tensor,
    train_mask: torch.Tensor,
    num_classes: int,
    coverage_target: float,
    alpha: float,
    cpd_risk_target: float = 0.15,
    max_prototypes_per_class: int = 1,
    min_points_per_proto: int = 16,
    prototype_bank_seed: int = 0,
    ova_gate: OVAGate | None = None,
    soft_consensus_risk_target: float | None = None,
    trust_consensus_risk_target: float | None = None,
    benign_reclaim_risk_target: float = 0.02,
    nonbenign_bridge_risk_target: float = 0.08,
    knn_k: int = 8,
    trust_k: int | None = None,
) -> DeferralCalibrator:
    temperature = fit_temperature(val_logits, val_labels)
    calibrated_val_logits = apply_temperature(val_logits, temperature)
    val_probs = torch.softmax(calibrated_val_logits, dim=1)
    aps_scores = aps_true_class_scores(val_probs, val_labels)
    aps_quantile = conformal_quantile(aps_scores, alpha=alpha)
    max_prob = torch.max(val_probs, dim=1).values.detach().cpu().numpy()
    confidence_threshold = float(np.quantile(max_prob, 1.0 - float(coverage_target), method="higher"))
    energy = torch.logsumexp(calibrated_val_logits, dim=1).detach().cpu().numpy()
    energy_threshold = float(np.quantile(energy, 1.0 - float(coverage_target), method="higher"))

    prototypes = build_class_prototypes(
        embeddings=train_embeddings,
        labels=train_labels,
        mask=train_mask,
        num_classes=num_classes,
    )
    multi_prototypes, multi_prototype_labels = build_multi_prototype_bank(
        embeddings=train_embeddings,
        labels=train_labels,
        mask=train_mask,
        num_classes=num_classes,
        max_prototypes_per_class=max_prototypes_per_class,
        min_points_per_proto=min_points_per_proto,
        random_seed=prototype_bank_seed,
    )
    support_embeddings = train_embeddings[train_mask].detach().cpu()
    support_labels = train_labels[train_mask].detach().cpu()
    knn_k_eff = max(int(knn_k), 1)
    trust_k_eff = max(int(knn_k if trust_k is None else trust_k), 1)
    val_pred = torch.argmax(calibrated_val_logits, dim=1)
    val_sets = aps_prediction_sets(val_probs, aps_quantile)
    singleton_mask = val_sets.sum(dim=1) == 1
    distances = prototype_distances(val_embeddings, prototypes)
    pred_distance = distances[torch.arange(val_pred.shape[0]), val_pred]
    multi_same_distance_np, _, multi_proto_margin_np, _ = multiproto_distance_features(
        embeddings=val_embeddings,
        prototypes=multi_prototypes,
        prototype_labels=multi_prototype_labels,
        pred=val_pred.detach().cpu().numpy().astype(np.int64, copy=False),
    )
    threshold_mask = singleton_mask & (val_pred == val_labels)
    if int(threshold_mask.sum().item()) <= 0:
        threshold_mask = val_pred == val_labels
    if int(threshold_mask.sum().item()) <= 0:
        threshold_mask = torch.ones_like(val_pred, dtype=torch.bool)
    prototype_threshold = float(
        np.quantile(
            pred_distance[threshold_mask].detach().cpu().numpy(),
            float(coverage_target),
            method="higher",
        )
    )
    prototype_thresholds = np.full((int(num_classes),), prototype_threshold, dtype=np.float64)
    multi_proto_distance_threshold = float(
        np.quantile(
            multi_same_distance_np[threshold_mask.detach().cpu().numpy().astype(bool, copy=False)],
            float(coverage_target),
            method="higher",
        )
    )
    multi_proto_distance_thresholds = np.full((int(num_classes),), multi_proto_distance_threshold, dtype=np.float64)
    multi_proto_margin_threshold = float(
        np.quantile(
            multi_proto_margin_np[threshold_mask.detach().cpu().numpy().astype(bool, copy=False)],
            1.0 - float(coverage_target),
            method="lower",
        )
    )
    multi_proto_margin_thresholds = np.full((int(num_classes),), multi_proto_margin_threshold, dtype=np.float64)
    pred_distance_np = pred_distance.detach().cpu().numpy().astype(np.float64, copy=False)
    val_pred_np = val_pred.detach().cpu().numpy().astype(np.int64, copy=False)
    val_label_np = val_labels.detach().cpu().numpy().astype(np.int64, copy=False)
    val_knn_distance_np = classwise_knn_distances(
        embeddings=val_embeddings,
        support_embeddings=support_embeddings,
        support_labels=support_labels,
        pred=val_pred_np,
        k=knn_k_eff,
    )
    val_trust_score_np = classwise_trust_scores(
        embeddings=val_embeddings,
        support_embeddings=support_embeddings,
        support_labels=support_labels,
        pred=val_pred_np,
        k=trust_k_eff,
    )
    for class_id in range(int(num_classes)):
        class_mask = threshold_mask.detach().cpu().numpy().astype(bool, copy=False) & (val_pred_np == int(class_id))
        if int(class_mask.sum()) <= 1:
            class_mask = (val_pred_np == int(class_id)) & (val_label_np == int(class_id))
        if int(class_mask.sum()) <= 1:
            continue
        prototype_thresholds[int(class_id)] = float(
            np.quantile(pred_distance_np[class_mask], float(coverage_target), method="higher")
        )
        multi_proto_distance_thresholds[int(class_id)] = float(
            np.quantile(multi_same_distance_np[class_mask], float(coverage_target), method="higher")
        )
        multi_proto_margin_thresholds[int(class_id)] = float(
            np.quantile(multi_proto_margin_np[class_mask], 1.0 - float(coverage_target), method="lower")
        )
    knn_distance_threshold = float(
        np.quantile(
            val_knn_distance_np[threshold_mask.detach().cpu().numpy().astype(bool, copy=False)],
            float(coverage_target),
            method="higher",
        )
    )
    knn_distance_thresholds = np.full((int(num_classes),), knn_distance_threshold, dtype=np.float64)
    trust_threshold = float(
        np.quantile(
            val_trust_score_np[threshold_mask.detach().cpu().numpy().astype(bool, copy=False)],
            1.0 - float(coverage_target),
            method="lower",
        )
    )
    trust_thresholds = np.full((int(num_classes),), trust_threshold, dtype=np.float64)
    for class_id in range(int(num_classes)):
        class_mask = threshold_mask.detach().cpu().numpy().astype(bool, copy=False) & (val_pred_np == int(class_id))
        if int(class_mask.sum()) <= 1:
            class_mask = (val_pred_np == int(class_id)) & (val_label_np == int(class_id))
        if int(class_mask.sum()) <= 1:
            continue
        knn_distance_thresholds[int(class_id)] = float(
            np.quantile(val_knn_distance_np[class_mask], float(coverage_target), method="higher")
        )
        trust_thresholds[int(class_id)] = float(
            np.quantile(val_trust_score_np[class_mask], 1.0 - float(coverage_target), method="lower")
        )

    max_prob_np = max_prob.astype(np.float64, copy=False)
    proto_margin_np = prototype_thresholds[val_pred_np] - pred_distance_np
    multi_proto_distance_margin_np = multi_proto_distance_thresholds[val_pred_np] - multi_same_distance_np
    multi_proto_margin_gap_np = multi_proto_margin_np - multi_proto_margin_thresholds[val_pred_np]
    knn_margin_np = knn_distance_thresholds[val_pred_np] - val_knn_distance_np
    trust_margin_np = val_trust_score_np - trust_thresholds[val_pred_np]
    aps_margin_np = max_prob_np - float(aps_quantile)
    confidence_margin_np = max_prob_np - float(confidence_threshold)
    conf_scale = _score_scale(confidence_margin_np)
    proto_scale = _score_scale(proto_margin_np)
    multi_proto_distance_scale = _score_scale(multi_proto_distance_margin_np)
    multi_proto_margin_scale = _score_scale(multi_proto_margin_gap_np)
    knn_scale = _score_scale(knn_margin_np)
    trust_scale = _score_scale(trust_margin_np)
    cpd_gate_mask = proto_margin_np >= 0.0
    cpd_scores = aps_margin_np[cpd_gate_mask]
    cpd_errors = (val_pred_np != val_label_np)[cpd_gate_mask]
    cpd_threshold, cpd_val_coverage, cpd_val_risk = _select_risk_bounded_threshold(
        scores=cpd_scores,
        errors=cpd_errors,
        risk_target=float(cpd_risk_target),
        coverage_cap=float(coverage_target),
        total_count=int(val_pred_np.shape[0]),
    )
    ova_score_scale = 1.0
    soft_consensus_threshold = float("inf")
    soft_consensus_target = float(
        cpd_risk_target if soft_consensus_risk_target is None else soft_consensus_risk_target
    )
    soft_consensus_val_coverage = 0.0
    soft_consensus_val_risk = 1.0
    trust_consensus_threshold = float("inf")
    trust_consensus_target = float(
        cpd_risk_target if trust_consensus_risk_target is None else trust_consensus_risk_target
    )
    trust_consensus_val_coverage = 0.0
    trust_consensus_val_risk = 1.0
    benign_reclaim_threshold = float("inf")
    benign_reclaim_val_coverage = 0.0
    benign_reclaim_val_risk = 1.0
    nonbenign_bridge_threshold = float("inf")
    nonbenign_bridge_val_coverage = 0.0
    nonbenign_bridge_val_risk = 1.0
    if ova_gate is not None:
        ova_probs = ova_probabilities(val_embeddings, ova_gate)
        ova_pred = np.argmax(ova_probs, axis=1).astype(np.int64, copy=False)
        ova_max_score = np.max(ova_probs, axis=1).astype(np.float64, copy=False)
        ova_margin = ova_max_score - float(ova_gate.threshold)
        ova_score_scale = _score_scale(ova_margin)
        soft_consensus_score = np.minimum.reduce(
            [
                confidence_margin_np / conf_scale,
                proto_margin_np / proto_scale,
                ova_margin / ova_score_scale,
            ]
        )
        soft_consensus_mask = ova_pred == val_pred_np
        soft_consensus_threshold, soft_consensus_val_coverage, soft_consensus_val_risk = _select_masked_risk_bounded_threshold(
            scores=soft_consensus_score,
            errors=val_pred_np != val_label_np,
            mask=soft_consensus_mask,
            risk_target=soft_consensus_target,
            coverage_cap=float(coverage_target),
            total_count=int(val_pred_np.shape[0]),
        )
        trust_consensus_score = np.minimum.reduce(
            [
                confidence_margin_np / conf_scale,
                proto_margin_np / proto_scale,
                trust_margin_np / trust_scale,
                ova_margin / ova_score_scale,
            ]
        )
        trust_consensus_mask = ova_pred == val_pred_np
        trust_consensus_threshold, trust_consensus_val_coverage, trust_consensus_val_risk = _select_masked_risk_bounded_threshold(
            scores=trust_consensus_score,
            errors=val_pred_np != val_label_np,
            mask=trust_consensus_mask,
            risk_target=trust_consensus_target,
            coverage_cap=float(coverage_target),
            total_count=int(val_pred_np.shape[0]),
        )

        benign_reclaim_score = np.minimum.reduce(
            [
                confidence_margin_np / conf_scale,
                proto_margin_np / proto_scale,
                ova_margin / ova_score_scale,
            ]
        )
        benign_reclaim_mask = (
            (val_pred_np == 0)
            & (ova_pred == 0)
            & (proto_margin_np >= 0.0)
            & (ova_margin >= 0.0)
        )
        benign_reclaim_threshold, benign_reclaim_val_coverage, benign_reclaim_val_risk = _select_masked_risk_bounded_threshold(
            scores=benign_reclaim_score,
            errors=val_label_np != 0,
            mask=benign_reclaim_mask,
            risk_target=float(benign_reclaim_risk_target),
            coverage_cap=1.0,
            total_count=int(val_pred_np.shape[0]),
        )
        nonbenign_bridge_mask = (
            (val_pred_np != 0)
            & (ova_pred == val_pred_np)
            & (proto_margin_np >= 0.0)
            & (ova_margin >= 0.0)
        )
        nonbenign_bridge_threshold, nonbenign_bridge_val_coverage, nonbenign_bridge_val_risk = _select_masked_risk_bounded_threshold(
            scores=soft_consensus_score,
            errors=val_pred_np != val_label_np,
            mask=nonbenign_bridge_mask,
            risk_target=float(nonbenign_bridge_risk_target),
            coverage_cap=1.0,
            total_count=int(val_pred_np.shape[0]),
        )
    return DeferralCalibrator(
        temperature=temperature,
        aps_quantile=aps_quantile,
        prototype_threshold=prototype_threshold,
        prototype_thresholds=prototype_thresholds,
        multi_proto_distance_threshold=multi_proto_distance_threshold,
        multi_proto_distance_thresholds=multi_proto_distance_thresholds,
        multi_proto_margin_threshold=multi_proto_margin_threshold,
        multi_proto_margin_thresholds=multi_proto_margin_thresholds,
        multi_proto_distance_scale=multi_proto_distance_scale,
        multi_proto_margin_scale=multi_proto_margin_scale,
        knn_distance_threshold=knn_distance_threshold,
        knn_distance_thresholds=knn_distance_thresholds,
        knn_distance_scale=knn_scale,
        knn_k=int(knn_k_eff),
        trust_threshold=trust_threshold,
        trust_thresholds=trust_thresholds,
        trust_score_scale=trust_scale,
        trust_k=int(trust_k_eff),
        confidence_threshold=confidence_threshold,
        energy_threshold=energy_threshold,
        coverage_target=float(coverage_target),
        alpha=float(alpha),
        cpd_threshold=cpd_threshold,
        cpd_risk_target=float(cpd_risk_target),
        cpd_conf_scale=conf_scale,
        cpd_proto_scale=proto_scale,
        cpd_val_coverage=cpd_val_coverage,
        cpd_val_risk=cpd_val_risk,
        ova_score_scale=ova_score_scale,
        soft_consensus_threshold=soft_consensus_threshold,
        soft_consensus_risk_target=soft_consensus_target,
        soft_consensus_val_coverage=soft_consensus_val_coverage,
        soft_consensus_val_risk=soft_consensus_val_risk,
        trust_consensus_threshold=trust_consensus_threshold,
        trust_consensus_risk_target=trust_consensus_target,
        trust_consensus_val_coverage=trust_consensus_val_coverage,
        trust_consensus_val_risk=trust_consensus_val_risk,
        benign_reclaim_threshold=benign_reclaim_threshold,
        benign_reclaim_risk_target=float(benign_reclaim_risk_target),
        benign_reclaim_val_coverage=benign_reclaim_val_coverage,
        benign_reclaim_val_risk=benign_reclaim_val_risk,
        nonbenign_bridge_threshold=nonbenign_bridge_threshold,
        nonbenign_bridge_risk_target=float(nonbenign_bridge_risk_target),
        nonbenign_bridge_val_coverage=nonbenign_bridge_val_coverage,
        nonbenign_bridge_val_risk=nonbenign_bridge_val_risk,
        prototypes=prototypes.detach().cpu(),
        multi_prototypes=multi_prototypes.detach().cpu(),
        multi_prototype_labels=multi_prototype_labels.detach().cpu(),
        support_embeddings=support_embeddings,
        support_labels=support_labels,
    )


def build_method_outputs(
    *,
    logits: torch.Tensor,
    embeddings: torch.Tensor,
    calibrator: DeferralCalibrator,
    ova_gate: OVAGate | None = None,
    review_selectors: dict[str, ReviewSelector] | None = None,
    target_adapt_momentum: float = 0.0,
    shift_reclaim_enabled: bool = False,
    shift_reclaim_momentum: float | None = None,
    shift_min_cohort: int = 8,
    shift_conf_quantile: float = 0.1,
    shift_ova_quantile: float = 0.1,
    shift_proto_quantile: float = 0.9,
    shift_multi_margin_quantile: float = 0.1,
    shift_hybrid_gain_quantile: float = 0.8,
    shift_hybrid_activation_coverage: float = 0.12,
    shift_hybrid_require_knn: bool = True,
    shift_hybrid_require_trust: bool = False,
) -> dict[str, dict[str, np.ndarray]]:
    calibrated_logits = apply_temperature(logits, calibrator.temperature)
    probs = torch.softmax(calibrated_logits, dim=1)
    pred = torch.argmax(calibrated_logits, dim=1)
    max_prob = torch.max(probs, dim=1).values
    aps_sets = aps_prediction_sets(probs, calibrator.aps_quantile)
    aps_singleton = aps_sets.sum(dim=1) == 1
    distances = prototype_distances(embeddings, calibrator.prototypes)
    pred_distance = distances[torch.arange(pred.shape[0]), pred]
    energy = torch.logsumexp(calibrated_logits, dim=1)

    aps_margin = (max_prob - float(calibrator.aps_quantile)).detach().cpu().numpy()
    pred_np = pred.detach().cpu().numpy().astype(np.int64, copy=False)
    proto_thresholds = np.asarray(calibrator.prototype_thresholds, dtype=np.float64)
    proto_margin = proto_thresholds[pred_np] - pred_distance.detach().cpu().numpy().astype(np.float64, copy=False)
    multi_same_distance, _, multi_proto_margin, _ = multiproto_distance_features(
        embeddings=embeddings,
        prototypes=calibrator.multi_prototypes,
        prototype_labels=calibrator.multi_prototype_labels,
        pred=pred_np,
    )
    multi_proto_distance_thresholds = np.asarray(calibrator.multi_proto_distance_thresholds, dtype=np.float64)
    multi_proto_margin_thresholds = np.asarray(calibrator.multi_proto_margin_thresholds, dtype=np.float64)
    multi_proto_distance_margin = multi_proto_distance_thresholds[pred_np] - multi_same_distance
    multi_proto_margin_gap = multi_proto_margin - multi_proto_margin_thresholds[pred_np]
    multiproto_gate_score = np.minimum(multi_proto_distance_margin, multi_proto_margin_gap)
    multiproto_lift = multi_proto_distance_margin - proto_margin
    knn_thresholds = np.asarray(calibrator.knn_distance_thresholds, dtype=np.float64)
    knn_distance = classwise_knn_distances(
        embeddings=embeddings,
        support_embeddings=calibrator.support_embeddings,
        support_labels=calibrator.support_labels,
        pred=pred_np,
        k=int(calibrator.knn_k),
    )
    knn_margin = knn_thresholds[pred_np] - knn_distance
    trust_thresholds = np.asarray(calibrator.trust_thresholds, dtype=np.float64)
    trust_score = classwise_trust_scores(
        embeddings=embeddings,
        support_embeddings=calibrator.support_embeddings,
        support_labels=calibrator.support_labels,
        pred=pred_np,
        k=int(calibrator.trust_k),
    )
    trust_margin = trust_score - trust_thresholds[pred_np]
    confidence_margin = (max_prob - float(calibrator.confidence_threshold)).detach().cpu().numpy()
    energy_margin = (energy - float(calibrator.energy_threshold)).detach().cpu().numpy()
    outputs = {
        "msp": {
            "pred": pred_np,
            "accept": confidence_margin >= 0.0,
            "score": confidence_margin,
        },
        "msp_nonbenign": {
            "pred": pred_np,
            "accept": (confidence_margin >= 0.0) & (pred_np != 0),
            "score": confidence_margin,
        },
        "energy": {
            "pred": pred_np,
            "accept": energy_margin >= 0.0,
            "score": energy_margin,
        },
        "energy_nonbenign": {
            "pred": pred_np,
            "accept": (energy_margin >= 0.0) & (pred_np != 0),
            "score": energy_margin,
        },
        "aps_only": {
            "pred": pred_np,
            "accept": aps_singleton.detach().cpu().numpy(),
            "score": aps_margin,
        },
        "prototype_only": {
            "pred": pred_np,
            "accept": proto_margin >= 0.0,
            "score": proto_margin,
        },
        "prototype_only_nonbenign": {
            "pred": pred_np,
            "accept": (proto_margin >= 0.0) & (pred_np != 0),
            "score": proto_margin,
        },
        "multiproto_only": {
            "pred": pred_np,
            "accept": (multi_proto_distance_margin >= 0.0) & (multi_proto_margin_gap >= 0.0),
            "score": multiproto_gate_score,
        },
        "multiproto_only_nonbenign": {
            "pred": pred_np,
            "accept": (multi_proto_distance_margin >= 0.0) & (multi_proto_margin_gap >= 0.0) & (pred_np != 0),
            "score": multiproto_gate_score,
        },
        "knn_only": {
            "pred": pred_np,
            "accept": knn_margin >= 0.0,
            "score": knn_margin,
        },
        "knn_only_nonbenign": {
            "pred": pred_np,
            "accept": (knn_margin >= 0.0) & (pred_np != 0),
            "score": knn_margin,
        },
        "trust_only": {
            "pred": pred_np,
            "accept": trust_margin >= 0.0,
            "score": trust_margin,
        },
        "trust_only_nonbenign": {
            "pred": pred_np,
            "accept": (trust_margin >= 0.0) & (pred_np != 0),
            "score": trust_margin,
        },
        "cpd_gate": {
            "pred": pred_np,
            "accept": (proto_margin >= 0.0) & (aps_margin >= float(calibrator.cpd_threshold)),
            "score": np.minimum(proto_margin, aps_margin - float(calibrator.cpd_threshold)),
        },
        "cpd_gate_nonbenign": {
            "pred": pred_np,
            "accept": (proto_margin >= 0.0) & (aps_margin >= float(calibrator.cpd_threshold)) & (pred_np != 0),
            "score": np.minimum(proto_margin, aps_margin - float(calibrator.cpd_threshold)),
        },
        "cpd_multiproto_gate": {
            "pred": pred_np,
            "accept": (multi_proto_distance_margin >= 0.0)
            & (multi_proto_margin_gap >= 0.0)
            & (aps_margin >= float(calibrator.cpd_threshold)),
            "score": np.minimum(multiproto_gate_score, aps_margin - float(calibrator.cpd_threshold)),
        },
        "cpd_multiproto_gate_nonbenign": {
            "pred": pred_np,
            "accept": (multi_proto_distance_margin >= 0.0)
            & (multi_proto_margin_gap >= 0.0)
            & (aps_margin >= float(calibrator.cpd_threshold))
            & (pred_np != 0),
            "score": np.minimum(multiproto_gate_score, aps_margin - float(calibrator.cpd_threshold)),
        },
        "cpd_knn_gate": {
            "pred": pred_np,
            "accept": (knn_margin >= 0.0) & (aps_margin >= float(calibrator.cpd_threshold)),
            "score": np.minimum(knn_margin, aps_margin - float(calibrator.cpd_threshold)),
        },
        "cpd_knn_gate_nonbenign": {
            "pred": pred_np,
            "accept": (knn_margin >= 0.0) & (aps_margin >= float(calibrator.cpd_threshold)) & (pred_np != 0),
            "score": np.minimum(knn_margin, aps_margin - float(calibrator.cpd_threshold)),
        },
        "cpd_strict": {
            "pred": pred_np,
            "accept": (aps_singleton.detach().cpu().numpy()) & (proto_margin >= 0.0),
            "score": np.minimum(aps_margin, proto_margin),
        },
    }
    if ova_gate is not None:
        ova_probs = ova_probabilities(embeddings, ova_gate)
        ova_pred = np.argmax(ova_probs, axis=1).astype(np.int64, copy=False)
        ova_max_score = np.max(ova_probs, axis=1)
        ova_margin = ova_max_score - float(ova_gate.threshold)
        trust_consensus_score = np.minimum.reduce(
            [
                confidence_margin / max(float(calibrator.cpd_conf_scale), 1e-6),
                proto_margin / max(float(calibrator.cpd_proto_scale), 1e-6),
                trust_margin / max(float(calibrator.trust_score_scale), 1e-6),
                ova_margin / max(float(calibrator.ova_score_scale), 1e-6),
            ]
        )
        soft_consensus_score = np.minimum.reduce(
            [
                confidence_margin / max(float(calibrator.cpd_conf_scale), 1e-6),
                proto_margin / max(float(calibrator.cpd_proto_scale), 1e-6),
                ova_margin / max(float(calibrator.ova_score_scale), 1e-6),
            ]
        )
        benign_reclaim_score = np.minimum.reduce(
            [
                confidence_margin / max(float(calibrator.cpd_conf_scale), 1e-6),
                proto_margin / max(float(calibrator.cpd_proto_scale), 1e-6),
                ova_margin / max(float(calibrator.ova_score_scale), 1e-6),
            ]
        )
        benign_reclaim_accept = (
            (pred_np == 0)
            & (ova_pred == 0)
            & (proto_margin >= 0.0)
            & (ova_margin >= 0.0)
            & (benign_reclaim_score >= float(calibrator.benign_reclaim_threshold))
        )
        outputs["ova_gate"] = {
            "pred": ova_pred,
            "accept": ova_margin >= 0.0,
            "score": ova_margin,
        }
        outputs["ova_gate_nonbenign"] = {
            "pred": ova_pred,
            "accept": (ova_margin >= 0.0) & (ova_pred != 0),
            "score": ova_margin,
        }
        outputs["ova_gate_agree"] = {
            "pred": ova_pred,
            "accept": (ova_margin >= 0.0) & (ova_pred == pred_np),
            "score": np.minimum(ova_margin, confidence_margin),
        }
        outputs["ova_gate_nonbenign_agree"] = {
            "pred": ova_pred,
            "accept": (ova_margin >= 0.0) & (ova_pred != 0) & (ova_pred == pred_np),
            "score": np.minimum(ova_margin, confidence_margin),
        }
        outputs["cpd_consensus"] = {
            "pred": pred_np,
            "accept": ((aps_singleton.detach().cpu().numpy()) & (proto_margin >= 0.0) & (ova_margin >= 0.0) & (ova_pred == pred_np)),
            "score": np.minimum(np.minimum(aps_margin, proto_margin), ova_margin),
        }
        outputs["cpd_multiproto_consensus"] = {
            "pred": pred_np,
            "accept": (aps_singleton.detach().cpu().numpy())
            & (multi_proto_distance_margin >= 0.0)
            & (multi_proto_margin_gap >= 0.0)
            & (ova_margin >= 0.0)
            & (ova_pred == pred_np),
            "score": np.minimum(np.minimum(aps_margin, multiproto_gate_score), ova_margin),
        }
        outputs["cpd_knn_consensus"] = {
            "pred": pred_np,
            "accept": ((aps_singleton.detach().cpu().numpy()) & (knn_margin >= 0.0) & (ova_margin >= 0.0) & (ova_pred == pred_np)),
            "score": np.minimum(np.minimum(aps_margin, knn_margin), ova_margin),
        }
        outputs["cpd_trust_consensus"] = {
            "pred": pred_np,
            "accept": ((aps_singleton.detach().cpu().numpy()) & (trust_margin >= 0.0) & (ova_margin >= 0.0) & (ova_pred == pred_np)),
            "score": np.minimum(np.minimum(aps_margin, trust_margin), ova_margin),
        }
        outputs["cpd_soft_consensus"] = {
            "pred": pred_np,
            "accept": (ova_pred == pred_np) & (soft_consensus_score >= float(calibrator.soft_consensus_threshold)),
            "score": soft_consensus_score,
        }
        outputs["cpd_trust_soft_consensus"] = {
            "pred": pred_np,
            "accept": (ova_pred == pred_np) & (trust_consensus_score >= float(calibrator.trust_consensus_threshold)),
            "score": trust_consensus_score,
        }
        outputs["cpd_knn_consensus_gate"] = {
            "pred": pred_np,
            "accept": (knn_margin >= 0.0)
            & (aps_margin >= float(calibrator.cpd_threshold))
            & (ova_margin >= 0.0)
            & (ova_pred == pred_np),
            "score": np.minimum(np.minimum(knn_margin, aps_margin - float(calibrator.cpd_threshold)), ova_margin),
        }
        outputs["cpd_trust_consensus_gate"] = {
            "pred": pred_np,
            "accept": (trust_margin >= 0.0)
            & (aps_margin >= float(calibrator.cpd_threshold))
            & (ova_margin >= 0.0)
            & (ova_pred == pred_np),
            "score": np.minimum(np.minimum(trust_margin, aps_margin - float(calibrator.cpd_threshold)), ova_margin),
        }
        outputs["cpd_multiproto_consensus_gate"] = {
            "pred": pred_np,
            "accept": (multi_proto_distance_margin >= 0.0)
            & (multi_proto_margin_gap >= 0.0)
            & (aps_margin >= float(calibrator.cpd_threshold))
            & (ova_margin >= 0.0)
            & (ova_pred == pred_np),
            "score": np.minimum(
                np.minimum(multiproto_gate_score, aps_margin - float(calibrator.cpd_threshold)),
                ova_margin,
            ),
        }
        outputs["cpd_proto_trust_consensus_gate"] = {
            "pred": pred_np,
            "accept": (proto_margin >= 0.0)
            & (trust_margin >= 0.0)
            & (aps_margin >= float(calibrator.cpd_threshold))
            & (ova_margin >= 0.0)
            & (ova_pred == pred_np),
            "score": np.minimum(
                np.minimum(np.minimum(proto_margin, trust_margin), aps_margin - float(calibrator.cpd_threshold)),
                ova_margin,
            ),
        }
        outputs["cpd_knn_trust_consensus_gate"] = {
            "pred": pred_np,
            "accept": (knn_margin >= 0.0)
            & (trust_margin >= 0.0)
            & (aps_margin >= float(calibrator.cpd_threshold))
            & (ova_margin >= 0.0)
            & (ova_pred == pred_np),
            "score": np.minimum(
                np.minimum(np.minimum(knn_margin, trust_margin), aps_margin - float(calibrator.cpd_threshold)),
                ova_margin,
            ),
        }
        outputs["cpd_proto_knn_consensus_gate"] = {
            "pred": pred_np,
            "accept": (proto_margin >= 0.0)
            & (knn_margin >= 0.0)
            & (aps_margin >= float(calibrator.cpd_threshold))
            & (ova_margin >= 0.0)
            & (ova_pred == pred_np),
            "score": np.minimum(
                np.minimum(np.minimum(proto_margin, knn_margin), aps_margin - float(calibrator.cpd_threshold)),
                ova_margin,
            ),
        }
        knn_soft_consensus_score = np.minimum(
            soft_consensus_score,
            knn_margin / max(float(calibrator.knn_distance_scale), 1e-6),
        )
        outputs["cpd_soft_knn_consensus"] = {
            "pred": pred_np,
            "accept": (ova_pred == pred_np)
            & (soft_consensus_score >= float(calibrator.soft_consensus_threshold))
            & (knn_margin >= 0.0),
            "score": knn_soft_consensus_score,
        }
        outputs["cpd_benign_reclaim"] = {
            "pred": pred_np,
            "accept": benign_reclaim_accept,
            "score": benign_reclaim_score,
        }
        outputs["cpd_consensus_plus"] = {
            "pred": pred_np,
            "accept": outputs["cpd_consensus"]["accept"] | benign_reclaim_accept,
            "score": np.maximum(
                np.minimum(np.minimum(aps_margin, proto_margin), ova_margin),
                benign_reclaim_score,
            ),
        }
        outputs["cpd_multiproto_consensus_plus"] = {
            "pred": pred_np,
            "accept": outputs["cpd_multiproto_consensus"]["accept"] | benign_reclaim_accept,
            "score": np.maximum(outputs["cpd_multiproto_consensus"]["score"], benign_reclaim_score),
        }
        outputs["cpd_trust_consensus_plus"] = {
            "pred": pred_np,
            "accept": outputs["cpd_trust_consensus"]["accept"] | benign_reclaim_accept,
            "score": np.maximum(outputs["cpd_trust_consensus"]["score"], benign_reclaim_score),
        }
        outputs["cpd_soft_consensus_plus"] = {
            "pred": pred_np,
            "accept": outputs["cpd_soft_consensus"]["accept"] | benign_reclaim_accept,
            "score": np.maximum(soft_consensus_score, benign_reclaim_score),
        }
        outputs["cpd_trust_soft_consensus_plus"] = {
            "pred": pred_np,
            "accept": outputs["cpd_trust_soft_consensus"]["accept"] | benign_reclaim_accept,
            "score": np.maximum(trust_consensus_score, benign_reclaim_score),
        }
        outputs["cpd_knn_consensus_plus"] = {
            "pred": pred_np,
            "accept": outputs["cpd_knn_consensus"]["accept"] | benign_reclaim_accept,
            "score": np.maximum(outputs["cpd_knn_consensus"]["score"], benign_reclaim_score),
        }
        outputs["cpd_trust_consensus_gate_plus"] = {
            "pred": pred_np,
            "accept": outputs["cpd_trust_consensus_gate"]["accept"] | benign_reclaim_accept,
            "score": np.maximum(outputs["cpd_trust_consensus_gate"]["score"], benign_reclaim_score),
        }
        outputs["cpd_multiproto_consensus_gate_plus"] = {
            "pred": pred_np,
            "accept": outputs["cpd_multiproto_consensus_gate"]["accept"] | benign_reclaim_accept,
            "score": np.maximum(outputs["cpd_multiproto_consensus_gate"]["score"], benign_reclaim_score),
        }
        outputs["cpd_proto_trust_consensus_gate_plus"] = {
            "pred": pred_np,
            "accept": outputs["cpd_proto_trust_consensus_gate"]["accept"] | benign_reclaim_accept,
            "score": np.maximum(outputs["cpd_proto_trust_consensus_gate"]["score"], benign_reclaim_score),
        }
        outputs["cpd_knn_trust_consensus_gate_plus"] = {
            "pred": pred_np,
            "accept": outputs["cpd_knn_trust_consensus_gate"]["accept"] | benign_reclaim_accept,
            "score": np.maximum(outputs["cpd_knn_trust_consensus_gate"]["score"], benign_reclaim_score),
        }
        outputs["cpd_knn_consensus_gate_plus"] = {
            "pred": pred_np,
            "accept": outputs["cpd_knn_consensus_gate"]["accept"] | benign_reclaim_accept,
            "score": np.maximum(outputs["cpd_knn_consensus_gate"]["score"], benign_reclaim_score),
        }
        outputs["cpd_proto_knn_consensus_gate_plus"] = {
            "pred": pred_np,
            "accept": outputs["cpd_proto_knn_consensus_gate"]["accept"] | benign_reclaim_accept,
            "score": np.maximum(outputs["cpd_proto_knn_consensus_gate"]["score"], benign_reclaim_score),
        }
        outputs["cpd_soft_knn_consensus_plus"] = {
            "pred": pred_np,
            "accept": outputs["cpd_soft_knn_consensus"]["accept"] | benign_reclaim_accept,
            "score": np.maximum(knn_soft_consensus_score, benign_reclaim_score),
        }
        nonbenign_bridge_accept = (
            (pred_np != 0)
            & (ova_pred == pred_np)
            & (proto_margin >= 0.0)
            & (ova_margin >= 0.0)
            & (soft_consensus_score >= float(calibrator.nonbenign_bridge_threshold))
        )
        outputs["cpd_nonbenign_bridge"] = {
            "pred": pred_np,
            "accept": nonbenign_bridge_accept,
            "score": soft_consensus_score,
        }
        outputs["cpd_pseudo_bridge"] = {
            "pred": pred_np,
            "accept": outputs["cpd_consensus_plus"]["accept"] | nonbenign_bridge_accept,
            "score": np.maximum(outputs["cpd_consensus_plus"]["score"], soft_consensus_score),
        }
        if review_selectors:
            review_features = _review_selector_feature_matrix(
                pred_np=pred_np,
                ova_pred=ova_pred,
                aps_singleton=aps_singleton.detach().cpu().numpy(),
                confidence_margin=confidence_margin,
                proto_margin=proto_margin,
                aps_margin=aps_margin,
                ova_margin=ova_margin,
                soft_consensus_score=soft_consensus_score,
                benign_reclaim_score=benign_reclaim_score,
            )
            for name, selector in review_selectors.items():
                if selector.mode == "benign_budget":
                    selector_score = np.where(
                        ova_pred != 0,
                        1.0 + ova_margin,
                        ova_margin + float(ova_gate.threshold),
                    )
                    selector_accept = (ova_margin >= 0.0) & (
                        (ova_pred != 0)
                        | ((ova_margin + float(ova_gate.threshold)) >= float(selector.benign_score_threshold))
                    )
                else:
                    selector_score = review_selector_scores(review_features, selector)
                    selector_accept = (ova_margin >= 0.0) & (selector_score >= float(selector.threshold))
                outputs[name] = {
                    "pred": ova_pred,
                    "accept": selector_accept,
                    "score": selector_score,
                }
            if "ova_gate_selective" in outputs:
                prototype_accept = np.asarray(outputs["prototype_only_nonbenign"]["accept"], dtype=bool, copy=False)
                selective_accept = np.asarray(outputs["ova_gate_selective"]["accept"], dtype=bool, copy=False)
                union_accept = prototype_accept | selective_accept
                union_pred = pred_np.copy()
                selective_only = selective_accept & (~prototype_accept)
                union_pred[selective_only] = ova_pred[selective_only]
                union_score = np.where(prototype_accept, proto_margin, np.asarray(outputs["ova_gate_selective"]["score"]))
                outputs["review_prototype_or_ova_selective"] = {
                    "pred": union_pred,
                    "accept": union_accept,
                    "score": union_score,
                }
        if bool(shift_reclaim_enabled):
            cohort_accept = np.asarray(outputs["cpd_consensus_plus"]["accept"], dtype=bool, copy=False)
            adapt_momentum = float(target_adapt_momentum if shift_reclaim_momentum is None else shift_reclaim_momentum)
            if adapt_momentum <= 0.0:
                adapt_momentum = 0.5
            adapted_plus_prototypes = adapt_prototypes_with_target(
                embeddings=embeddings,
                pred=pred_np,
                accept=cohort_accept,
                prototypes=calibrator.prototypes,
                momentum=adapt_momentum,
            )
            adapted_plus_distances = prototype_distances(embeddings, adapted_plus_prototypes)
            adapted_plus_pred_distance = adapted_plus_distances[torch.arange(pred.shape[0]), pred]
            adapted_plus_pred_distance_np = adapted_plus_pred_distance.detach().cpu().numpy().astype(np.float64, copy=False)
            cohort_proto_thresholds = _classwise_quantile_thresholds(
                values=adapted_plus_pred_distance_np,
                pred=pred_np,
                accept=cohort_accept,
                num_classes=int(proto_thresholds.shape[0]),
                quantile=float(shift_proto_quantile),
                min_count=int(shift_min_cohort),
                default=np.asarray(proto_thresholds, dtype=np.float64),
                use_upper=True,
            )
            cohort_conf_thresholds = _classwise_quantile_thresholds(
                values=max_prob.detach().cpu().numpy().astype(np.float64, copy=False),
                pred=pred_np,
                accept=cohort_accept,
                num_classes=int(proto_thresholds.shape[0]),
                quantile=float(shift_conf_quantile),
                min_count=int(shift_min_cohort),
                default=np.full((int(proto_thresholds.shape[0]),), float(calibrator.confidence_threshold), dtype=np.float64),
                use_upper=False,
            )
            cohort_ova_thresholds = _classwise_quantile_thresholds(
                values=ova_max_score.astype(np.float64, copy=False),
                pred=pred_np,
                accept=cohort_accept,
                num_classes=int(proto_thresholds.shape[0]),
                quantile=float(shift_ova_quantile),
                min_count=int(shift_min_cohort),
                default=np.full((int(proto_thresholds.shape[0]),), float(ova_gate.threshold), dtype=np.float64),
                use_upper=False,
            )
            cohort_counts = np.bincount(pred_np[cohort_accept], minlength=int(proto_thresholds.shape[0]))
            class_ready = cohort_counts[pred_np] >= int(shift_min_cohort)
            shift_proto_margin = cohort_proto_thresholds[pred_np] - adapted_plus_pred_distance_np
            shift_conf_margin = max_prob.detach().cpu().numpy().astype(np.float64, copy=False) - cohort_conf_thresholds[pred_np]
            shift_ova_margin = ova_max_score.astype(np.float64, copy=False) - cohort_ova_thresholds[pred_np]
            shift_reclaim_accept = (
                (~cohort_accept)
                & class_ready
                & (pred_np == ova_pred)
                & (shift_proto_margin >= 0.0)
                & (shift_conf_margin >= 0.0)
                & (shift_ova_margin >= 0.0)
            )
            shift_reclaim_score = np.minimum.reduce(
                [
                    shift_proto_margin / max(float(calibrator.cpd_proto_scale), 1e-6),
                    shift_conf_margin / max(float(calibrator.cpd_conf_scale), 1e-6),
                    shift_ova_margin / max(float(calibrator.ova_score_scale), 1e-6),
                ]
            )
            outputs["cpd_shift_reclaim"] = {
                "pred": pred_np,
                "accept": shift_reclaim_accept,
                "score": shift_reclaim_score,
            }
            outputs["cpd_shift_consensus_plus"] = {
                "pred": pred_np,
                "accept": cohort_accept | shift_reclaim_accept,
                "score": np.maximum(outputs["cpd_consensus_plus"]["score"], shift_reclaim_score),
            }
            multiproto_cohort_accept = np.asarray(outputs["cpd_multiproto_consensus_plus"]["accept"], dtype=bool, copy=False)
            cohort_multi_distance_thresholds = _classwise_quantile_thresholds(
                values=multi_same_distance,
                pred=pred_np,
                accept=multiproto_cohort_accept,
                num_classes=int(proto_thresholds.shape[0]),
                quantile=float(shift_proto_quantile),
                min_count=int(shift_min_cohort),
                default=np.asarray(multi_proto_distance_thresholds, dtype=np.float64),
                use_upper=True,
            )
            cohort_multi_margin_thresholds = _classwise_quantile_thresholds(
                values=multi_proto_margin,
                pred=pred_np,
                accept=multiproto_cohort_accept,
                num_classes=int(proto_thresholds.shape[0]),
                quantile=float(shift_multi_margin_quantile),
                min_count=int(shift_min_cohort),
                default=np.asarray(multi_proto_margin_thresholds, dtype=np.float64),
                use_upper=False,
            )
            multiproto_counts = np.bincount(pred_np[multiproto_cohort_accept], minlength=int(proto_thresholds.shape[0]))
            multiproto_class_ready = multiproto_counts[pred_np] >= int(shift_min_cohort)
            shift_multiproto_distance_margin = cohort_multi_distance_thresholds[pred_np] - multi_same_distance
            shift_multiproto_margin_gap = multi_proto_margin - cohort_multi_margin_thresholds[pred_np]
            shift_multiproto_reclaim_accept = (
                (~multiproto_cohort_accept)
                & multiproto_class_ready
                & (pred_np == ova_pred)
                & (shift_multiproto_distance_margin >= 0.0)
                & (shift_multiproto_margin_gap >= 0.0)
                & (shift_conf_margin >= 0.0)
                & (shift_ova_margin >= 0.0)
            )
            shift_multiproto_score = np.minimum.reduce(
                [
                    shift_multiproto_distance_margin / max(float(calibrator.multi_proto_distance_scale), 1e-6),
                    shift_multiproto_margin_gap / max(float(calibrator.multi_proto_margin_scale), 1e-6),
                    shift_conf_margin / max(float(calibrator.cpd_conf_scale), 1e-6),
                    shift_ova_margin / max(float(calibrator.ova_score_scale), 1e-6),
                ]
            )
            outputs["cpd_shift_multiproto_consensus_plus"] = {
                "pred": pred_np,
                "accept": multiproto_cohort_accept | shift_multiproto_reclaim_accept,
                "score": np.maximum(outputs["cpd_multiproto_consensus_plus"]["score"], shift_multiproto_score),
            }
            multiproto_gate_cohort_accept = np.asarray(
                outputs["cpd_multiproto_consensus_gate_plus"]["accept"],
                dtype=bool,
                copy=False,
            )
            shift_multiproto_gate_accept = (
                shift_multiproto_reclaim_accept
                & (aps_margin >= float(calibrator.cpd_threshold))
                & (~multiproto_gate_cohort_accept)
            )
            shift_multiproto_gate_score = np.minimum(
                shift_multiproto_score,
                aps_margin - float(calibrator.cpd_threshold),
            )
            outputs["cpd_shift_multiproto_consensus_gate_plus"] = {
                "pred": pred_np,
                "accept": multiproto_gate_cohort_accept | shift_multiproto_gate_accept,
                "score": np.maximum(outputs["cpd_multiproto_consensus_gate_plus"]["score"], shift_multiproto_gate_score),
            }
            hybrid_gain_cohort_accept = np.asarray(
                outputs["cpd_shift_multiproto_consensus_plus"]["accept"],
                dtype=bool,
                copy=False,
            )
            hybrid_base_coverage = float(hybrid_gain_cohort_accept.mean()) if hybrid_gain_cohort_accept.size > 0 else 0.0
            hybrid_gate_enabled = hybrid_base_coverage <= float(shift_hybrid_activation_coverage)
            if hybrid_gate_enabled:
                outputs["cpd_shift_multiproto_coverage_switch_plus"] = {
                    "pred": pred_np,
                    "accept": np.asarray(outputs["cpd_shift_multiproto_consensus_gate_plus"]["accept"], dtype=bool, copy=False),
                    "score": np.asarray(outputs["cpd_shift_multiproto_consensus_gate_plus"]["score"], dtype=np.float64, copy=False),
                }
            else:
                outputs["cpd_shift_multiproto_coverage_switch_plus"] = {
                    "pred": pred_np,
                    "accept": hybrid_gain_cohort_accept.copy(),
                    "score": np.asarray(outputs["cpd_shift_multiproto_consensus_plus"]["score"], dtype=np.float64, copy=False),
                }
            selective_gate_accept = (
                np.asarray(outputs["cpd_shift_multiproto_consensus_gate_plus"]["accept"], dtype=bool, copy=False)
                & (~hybrid_gain_cohort_accept)
                & (pred_np != 0)
            )
            if not hybrid_gate_enabled:
                selective_gate_accept = np.zeros_like(selective_gate_accept, dtype=bool)
            if bool(shift_hybrid_require_knn):
                selective_gate_accept &= knn_margin >= 0.0
            if bool(shift_hybrid_require_trust):
                selective_gate_accept &= trust_margin >= 0.0
            selective_gate_score = np.asarray(
                outputs["cpd_shift_multiproto_consensus_gate_plus"]["score"],
                dtype=np.float64,
                copy=False,
            )
            if bool(shift_hybrid_require_knn):
                selective_gate_score = np.minimum(
                    selective_gate_score,
                    knn_margin / max(float(calibrator.knn_distance_scale), 1e-6),
                )
            if bool(shift_hybrid_require_trust):
                selective_gate_score = np.minimum(
                    selective_gate_score,
                    trust_margin / max(float(calibrator.trust_score_scale), 1e-6),
                )
            outputs["cpd_shift_multiproto_selective_gate_plus"] = {
                "pred": pred_np,
                "accept": hybrid_gain_cohort_accept | selective_gate_accept,
                "score": np.maximum(outputs["cpd_shift_multiproto_consensus_plus"]["score"], selective_gate_score),
            }
            shift_trust_score = np.minimum(
                shift_reclaim_score,
                trust_margin / max(float(calibrator.trust_score_scale), 1e-6),
            )
            trust_cohort_accept = np.asarray(outputs["cpd_trust_soft_consensus_plus"]["accept"], dtype=bool, copy=False)
            trust_shift_reclaim_accept = shift_reclaim_accept & (trust_margin >= 0.0) & (~trust_cohort_accept)
            outputs["cpd_shift_trust_soft_consensus_plus"] = {
                "pred": pred_np,
                "accept": trust_cohort_accept | trust_shift_reclaim_accept,
                "score": np.maximum(outputs["cpd_trust_soft_consensus_plus"]["score"], shift_trust_score),
            }
            trust_gate_cohort_accept = np.asarray(outputs["cpd_trust_consensus_gate_plus"]["accept"], dtype=bool, copy=False)
            trust_gate_shift_accept = (
                shift_reclaim_accept
                & (trust_margin >= 0.0)
                & (aps_margin >= float(calibrator.cpd_threshold))
                & (~trust_gate_cohort_accept)
            )
            trust_gate_shift_score = np.minimum(
                shift_trust_score,
                aps_margin - float(calibrator.cpd_threshold),
            )
            outputs["cpd_shift_trust_consensus_gate_plus"] = {
                "pred": pred_np,
                "accept": trust_gate_cohort_accept | trust_gate_shift_accept,
                "score": np.maximum(outputs["cpd_trust_consensus_gate_plus"]["score"], trust_gate_shift_score),
            }
            knn_trust_gate_cohort_accept = np.asarray(outputs["cpd_knn_trust_consensus_gate_plus"]["accept"], dtype=bool, copy=False)
            knn_trust_gate_shift_accept = trust_gate_shift_accept & (knn_margin >= 0.0) & (~knn_trust_gate_cohort_accept)
            knn_trust_gate_shift_score = np.minimum(
                trust_gate_shift_score,
                knn_margin / max(float(calibrator.knn_distance_scale), 1e-6),
            )
            outputs["cpd_shift_knn_trust_consensus_gate_plus"] = {
                "pred": pred_np,
                "accept": knn_trust_gate_cohort_accept | knn_trust_gate_shift_accept,
                "score": np.maximum(outputs["cpd_knn_trust_consensus_gate_plus"]["score"], knn_trust_gate_shift_score),
            }
        if float(target_adapt_momentum) > 0.0:
            adapted_prototypes = adapt_prototypes_with_target(
                embeddings=embeddings,
                pred=pred_np,
                accept=outputs["cpd_consensus"]["accept"],
                prototypes=calibrator.prototypes,
                momentum=float(target_adapt_momentum),
            )
            adapted_distances = prototype_distances(embeddings, adapted_prototypes)
            adapted_pred_distance = adapted_distances[torch.arange(pred.shape[0]), pred]
            adapted_proto_margin = proto_thresholds[pred_np] - adapted_pred_distance.detach().cpu().numpy().astype(np.float64, copy=False)
            outputs["cpd_adapt"] = {
                "pred": pred_np,
                "accept": (aps_singleton.detach().cpu().numpy()) & (adapted_proto_margin >= 0.0),
                "score": np.minimum(aps_margin, adapted_proto_margin),
            }
            outputs["cpd_adapt_consensus"] = {
                "pred": pred_np,
                "accept": ((aps_singleton.detach().cpu().numpy()) & (adapted_proto_margin >= 0.0) & (ova_margin >= 0.0) & (ova_pred == pred_np)),
                "score": np.minimum(np.minimum(aps_margin, adapted_proto_margin), ova_margin),
            }
    return outputs
