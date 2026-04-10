from __future__ import annotations

import numpy as np
from sklearn.metrics import f1_score


def safe_ratio(num: float, den: float) -> float:
    return float(num / den) if float(den) > 0.0 else 0.0


def risk_coverage_curve(labels: np.ndarray, pred: np.ndarray, score: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    order = np.argsort(-score, kind="stable")
    ordered_labels = labels[order]
    ordered_pred = pred[order]
    ordered_error = ((ordered_labels < 0) | (ordered_pred != ordered_labels)).astype(np.float64)
    cumulative_error = np.cumsum(ordered_error)
    coverage = np.arange(1, len(order) + 1, dtype=np.float64) / max(len(order), 1)
    risk = cumulative_error / np.arange(1, len(order) + 1, dtype=np.float64)
    aurc = float(np.trapz(risk, coverage))
    return coverage, risk, aurc


def evaluate_method(
    *,
    labels: np.ndarray,
    pred: np.ndarray,
    accept: np.ndarray,
    score: np.ndarray,
    benign_label: int = 0,
) -> dict[str, float | int]:
    labels = labels.astype(np.int64, copy=False)
    pred = pred.astype(np.int64, copy=False)
    accept = accept.astype(bool, copy=False)
    score = score.astype(np.float64, copy=False)

    benign_mask = labels == int(benign_label)
    known_mask = labels >= 0
    known_bot_mask = labels > int(benign_label)
    unknown_mask = labels < 0
    accepted = accept
    accepted_error = accepted & ((~known_mask) | (pred != labels))

    accepted_benign_fp = benign_mask & accepted & (pred != int(benign_label))
    accepted_correct_known_bot = known_bot_mask & accepted & (pred == labels)
    unknown_defer = unknown_mask & (~accepted)
    unknown_misroute = unknown_mask & accepted

    accepted_known_mask = known_mask & accepted
    if int(accepted_known_mask.sum()) > 0:
        accepted_known_macro_f1 = float(
            f1_score(labels[accepted_known_mask], pred[accepted_known_mask], average="macro", zero_division=0)
        )
    else:
        accepted_known_macro_f1 = 0.0
    if int(known_mask.sum()) > 0:
        closed_known_macro_f1 = float(f1_score(labels[known_mask], pred[known_mask], average="macro", zero_division=0))
    else:
        closed_known_macro_f1 = 0.0

    coverage_curve, risk_curve, aurc = risk_coverage_curve(labels=labels, pred=pred, score=score)
    return {
        "num_samples": int(labels.shape[0]),
        "num_accepted": int(accepted.sum()),
        "num_unknown": int(unknown_mask.sum()),
        "coverage": safe_ratio(float(accepted.sum()), float(labels.shape[0])),
        "selective_risk": safe_ratio(float(accepted_error.sum()), float(accepted.sum())),
        "accepted_benign_fpr": safe_ratio(float(accepted_benign_fp.sum()), float(benign_mask.sum())),
        "accepted_known_bot_miss_rate": 1.0 - safe_ratio(float(accepted_correct_known_bot.sum()), float(known_bot_mask.sum())),
        "unknown_to_defer_rate": safe_ratio(float(unknown_defer.sum()), float(unknown_mask.sum())),
        "unknown_misroute_rate": safe_ratio(float(unknown_misroute.sum()), float(unknown_mask.sum())),
        "alerts_per_10k_benign": 10000.0 * safe_ratio(float(accepted_benign_fp.sum()), float(benign_mask.sum())),
        "accepted_known_macro_f1": float(accepted_known_macro_f1),
        "closed_known_macro_f1": float(closed_known_macro_f1),
        "aurc": float(aurc),
        "curve_points": int(len(coverage_curve)),
    }


def evaluate_triage_policy(
    *,
    labels: np.ndarray,
    auto_pred: np.ndarray,
    auto_accept: np.ndarray,
    review_pred: np.ndarray,
    review_accept: np.ndarray,
    benign_label: int = 0,
) -> dict[str, float | int]:
    labels = labels.astype(np.int64, copy=False)
    auto_pred = auto_pred.astype(np.int64, copy=False)
    auto_accept = auto_accept.astype(bool, copy=False)
    review_pred = review_pred.astype(np.int64, copy=False)
    review_accept = review_accept.astype(bool, copy=False)

    benign_mask = labels == int(benign_label)
    known_mask = labels >= 0
    unknown_mask = labels < 0
    review_mask = (~auto_accept) & review_accept
    final_defer = ~(auto_accept | review_mask)

    auto_errors = auto_accept & ((~known_mask) | (auto_pred != labels))
    auto_unknown = auto_accept & unknown_mask
    review_unknown = review_mask & unknown_mask
    review_benign = review_mask & benign_mask
    actionable_mask = auto_accept | review_mask

    if int(review_mask.sum()) > 0 and int((known_mask & review_mask).sum()) > 0:
        review_known_macro_f1 = float(
            f1_score(labels[known_mask & review_mask], review_pred[known_mask & review_mask], average="macro", zero_division=0)
        )
    else:
        review_known_macro_f1 = 0.0

    if int((known_mask & actionable_mask).sum()) > 0:
        combined_pred = auto_pred.copy()
        combined_pred[review_mask] = review_pred[review_mask]
        actionable_known_macro_f1 = float(
            f1_score(labels[known_mask & actionable_mask], combined_pred[known_mask & actionable_mask], average="macro", zero_division=0)
        )
    else:
        actionable_known_macro_f1 = 0.0

    return {
        "num_samples": int(labels.shape[0]),
        "num_auto": int(auto_accept.sum()),
        "num_review": int(review_mask.sum()),
        "num_final_defer": int(final_defer.sum()),
        "auto_coverage": safe_ratio(float(auto_accept.sum()), float(labels.shape[0])),
        "review_coverage": safe_ratio(float(review_mask.sum()), float(labels.shape[0])),
        "actionable_coverage": safe_ratio(float(actionable_mask.sum()), float(labels.shape[0])),
        "final_defer_rate": safe_ratio(float(final_defer.sum()), float(labels.shape[0])),
        "auto_selective_risk": safe_ratio(float(auto_errors.sum()), float(auto_accept.sum())),
        "auto_unknown_misroute_rate": safe_ratio(float(auto_unknown.sum()), float(unknown_mask.sum())),
        "review_unknown_capture_rate": safe_ratio(float(review_unknown.sum()), float(unknown_mask.sum())),
        "review_benign_rate": safe_ratio(float(review_benign.sum()), float(benign_mask.sum())),
        "safe_unknown_handling_rate": 1.0 - safe_ratio(float(auto_unknown.sum()), float(unknown_mask.sum())),
        "review_known_macro_f1": review_known_macro_f1,
        "actionable_known_macro_f1": actionable_known_macro_f1,
    }
