from __future__ import annotations

from math import comb

import numpy as np


HIGHER_IS_BETTER = {
    "coverage",
    "unknown_to_defer_rate",
    "accepted_known_macro_f1",
    "closed_known_macro_f1",
}


def metric_benefit(reference_value: float, comparator_value: float, metric: str) -> float:
    metric_name = str(metric)
    if metric_name in HIGHER_IS_BETTER:
        return float(reference_value - comparator_value)
    return float(comparator_value - reference_value)


def sign_test_pvalue(wins: int, losses: int) -> float:
    wins = int(wins)
    losses = int(losses)
    total = wins + losses
    if total <= 0:
        return 1.0
    cutoff = min(wins, losses)
    prob = sum(comb(total, idx) for idx in range(cutoff + 1)) / float(2**total)
    return float(min(1.0, 2.0 * prob))


def hierarchical_paired_bootstrap_ci(
    diffs_by_protocol: dict[str, np.ndarray],
    *,
    num_bootstrap: int,
    seed: int,
) -> tuple[float, float, float]:
    protocols = sorted(diffs_by_protocol)
    if not protocols:
        return 0.0, 0.0, 0.0

    base = np.asarray([np.asarray(diffs_by_protocol[name], dtype=np.float64).mean() for name in protocols], dtype=np.float64)
    point_estimate = float(base.mean()) if base.size > 0 else 0.0
    rng = np.random.default_rng(int(seed))
    boot = np.zeros(int(num_bootstrap), dtype=np.float64)
    protocol_count = len(protocols)
    for idx in range(int(num_bootstrap)):
        sampled_means: list[float] = []
        protocol_sample = rng.integers(0, protocol_count, size=protocol_count)
        for protocol_idx in protocol_sample.tolist():
            diffs = np.asarray(diffs_by_protocol[protocols[int(protocol_idx)]], dtype=np.float64)
            if diffs.size <= 0:
                continue
            seed_sample = rng.integers(0, diffs.size, size=diffs.size)
            sampled_means.append(float(diffs[seed_sample].mean()))
        boot[idx] = float(np.mean(sampled_means)) if sampled_means else 0.0
    ci_low = float(np.quantile(boot, 0.025))
    ci_high = float(np.quantile(boot, 0.975))
    return point_estimate, ci_low, ci_high
