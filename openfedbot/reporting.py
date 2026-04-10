from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


def write_rows_csv(path: str | Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def aggregate_rows(
    rows: list[dict[str, object]],
    *,
    group_keys: list[str],
    metric_keys: list[str],
) -> list[dict[str, object]]:
    grouped: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[key] for key in group_keys)].append(row)

    out: list[dict[str, object]] = []
    for key, group_rows in sorted(grouped.items()):
        row_out = {group_key: value for group_key, value in zip(group_keys, key)}
        row_out["num_runs"] = len(group_rows)
        for metric in metric_keys:
            values = np.asarray([float(item[metric]) for item in group_rows], dtype=np.float64)
            row_out[f"{metric}_mean"] = float(values.mean())
            row_out[f"{metric}_std"] = float(values.std(ddof=0))
        out.append(row_out)
    return out


def plot_risk_coverage(curves: dict[str, dict[str, np.ndarray]], path: str | Path, title: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7, 5))
    for method, payload in curves.items():
        plt.plot(payload["coverage"], payload["risk"], label=method, linewidth=2)
    plt.xlabel("Coverage")
    plt.ylabel("Selective Risk")
    plt.title(title)
    plt.grid(alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out, dpi=180)
    plt.close()


def plot_unknown_routing(rows: list[dict[str, object]], path: str | Path, title: str) -> None:
    methods = [str(row["method"]) for row in rows]
    defer = np.asarray([float(row["unknown_to_defer_rate_mean"]) for row in rows], dtype=np.float64)
    misroute = np.asarray([float(row["unknown_misroute_rate_mean"]) for row in rows], dtype=np.float64)
    x = np.arange(len(methods))
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 5))
    plt.bar(x - 0.18, defer, width=0.36, label="unknown->defer")
    plt.bar(x + 0.18, misroute, width=0.36, label="unknown misroute")
    plt.xticks(x, methods, rotation=20, ha="right")
    plt.ylim(0.0, 1.0)
    plt.ylabel("Rate")
    plt.title(title)
    plt.grid(axis="y", alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out, dpi=180)
    plt.close()


def plot_operating_frontier(rows: list[dict[str, object]], path: str | Path, title: str) -> None:
    if not rows:
        return

    relation_rank = {"cross": 0, "same": 1}
    relations = sorted(
        {str(row.get("scenario_relation", "overall")) for row in rows},
        key=lambda item: (relation_rank.get(item, 99), item),
    )
    styles = {
        "auto": {"marker": "o", "color": "#1f77b4"},
        "triage": {"marker": "s", "color": "#d62728"},
    }

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, len(relations), figsize=(7 * max(len(relations), 1), 5), sharey=True)
    if len(relations) == 1:
        axes = [axes]

    for axis, relation in zip(axes, relations):
        subset = [row for row in rows if str(row.get("scenario_relation", "overall")) == relation]
        for row in subset:
            category = str(row.get("category", "auto"))
            style = styles.get(category, styles["auto"])
            x_value = float(row["operating_coverage"])
            y_value = float(row["safe_unknown_handling"])
            label = str(row.get("label", "point"))
            axis.scatter(x_value, y_value, s=110, marker=style["marker"], color=style["color"], alpha=0.9)
            axis.annotate(label, (x_value, y_value), textcoords="offset points", xytext=(5, 4), fontsize=8)
        axis.set_title(relation)
        axis.set_xlabel("Coverage / Actionable Coverage")
        axis.grid(alpha=0.25)
        axis.set_xlim(-0.02, 1.02)
        axis.set_ylim(-0.02, 1.02)

    axes[0].set_ylabel("Safe Unknown Handling")
    fig.suptitle(title)
    fig.tight_layout()
    plt.savefig(out, dpi=180)
    plt.close(fig)
