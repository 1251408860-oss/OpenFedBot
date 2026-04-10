#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from textwrap import fill

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from openfedbot.common import ensure_dir, save_json, timestamp_utc


PALETTE = {
    "black": "#000000",
    "orange": "#E69F00",
    "sky": "#56B4E9",
    "green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "vermillion": "#D55E00",
    "purple": "#CC79A7",
    "gray": "#8A8F98",
    "light_gray": "#D7DCE2",
    "dark_gray": "#4A4F55",
    "soft_blue": "#DCEAF7",
    "soft_orange": "#F9E8CC",
    "soft_green": "#D9F0E7",
    "soft_red": "#F9E1DA",
}

METHOD_LABELS = {
    "cpd_shift_multiproto_consensus_plus": "Multiproto safe backbone",
    "cpd_shift_consensus_plus": "Shift-consensus backbone",
    "cpd_shift_multiproto_coverage_switch_plus": "Coverage-switch auto line",
    "cpd_shift_multiproto_consensus_gate_plus": "Gate-plus auto line",
    "ova_gate": "OVA",
    "msp": "MSP",
    "energy": "Energy",
}

SCATTER_LABELS = {
    "cpd_shift_multiproto_consensus_plus": "Multiproto",
    "cpd_shift_consensus_plus": "Shift-consensus",
    "cpd_shift_multiproto_coverage_switch_plus": "Coverage-switch",
    "ova_gate": "OVA",
    "msp": "MSP",
    "energy": "Energy",
}

SCATTER_LABEL_OFFSETS = {
    "cross": {
        "cpd_shift_multiproto_consensus_plus": (-0.8, 1.0, "right", "bottom"),
        "cpd_shift_consensus_plus": (0.9, -0.8, "left", "top"),
        "cpd_shift_multiproto_coverage_switch_plus": (1.5, 0.3, "left", "bottom"),
        "ova_gate": (-1.3, 0.8, "right", "bottom"),
        "msp": (0.9, 1.0, "left", "bottom"),
        "energy": (1.2, -0.7, "left", "top"),
    },
    "same": {
        "cpd_shift_multiproto_consensus_plus": (-0.8, 0.9, "right", "bottom"),
        "cpd_shift_consensus_plus": (0.8, -0.9, "left", "top"),
        "cpd_shift_multiproto_coverage_switch_plus": (1.4, 0.3, "left", "bottom"),
        "ova_gate": (-1.0, -0.1, "right", "top"),
        "msp": (-1.0, -0.8, "right", "top"),
        "energy": (-1.0, 0.7, "right", "bottom"),
    },
}

METHOD_COLORS = {
    "cpd_shift_multiproto_consensus_plus": PALETTE["blue"],
    "cpd_shift_consensus_plus": PALETTE["green"],
    "cpd_shift_multiproto_coverage_switch_plus": PALETTE["vermillion"],
    "cpd_shift_multiproto_consensus_gate_plus": PALETTE["orange"],
    "ova_gate": PALETTE["gray"],
    "msp": "#A0A6AD",
    "energy": "#C3C7CC",
}

METHOD_MARKERS = {
    "cpd_shift_multiproto_consensus_plus": "o",
    "cpd_shift_consensus_plus": "s",
    "cpd_shift_multiproto_coverage_switch_plus": "D",
    "cpd_shift_multiproto_consensus_gate_plus": "P",
    "ova_gate": "^",
    "msp": "v",
    "energy": "X",
}

PROTOCOL_LABELS = {
    "h_to_e_slowburn": "H→E slowburn",
    "h_to_e_burst": "H→E burst",
    "e_to_h_slowburn": "E→H slowburn",
    "h_to_e_mimic": "H→E mimic",
    "e_to_h_mimic": "E→H mimic",
    "e_to_h_burst": "E→H burst",
    "same_e_slowburn": "same-E slowburn",
    "same_h_mimic": "same-H mimic",
    "same_h_burst": "same-H burst",
    "same_e_burst": "same-E burst",
    "same_h_slowburn": "same-H slowburn",
    "same_e_mimic": "same-E mimic",
}

THRESHOLD_COLORS = {
    0.10: PALETTE["sky"],
    0.12: PALETTE["blue"],
    0.14: PALETTE["vermillion"],
}

FOREST_METRICS = [
    "accepted_benign_fpr",
    "unknown_misroute_rate",
    "coverage",
    "aurc",
]

FOREST_LABELS = {
    "accepted_benign_fpr": "Benign FPR ↓",
    "unknown_misroute_rate": "Unknown misroute ↓",
    "coverage": "Coverage ↑",
    "aurc": "AURC ↓",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build four paper-facing WASA main figures")
    parser.add_argument(
        "--digest-dir",
        default="results/digest_cov12/reinforced_digest_20260408T040419Z",
    )
    parser.add_argument(
        "--cov10-digest-dir",
        default="results/digest_cov10/reinforced_digest_20260408T040323Z",
    )
    parser.add_argument(
        "--cov14-digest-dir",
        default="results/digest_cov14/reinforced_digest_20260408T040323Z",
    )
    parser.add_argument("--output-root", default="results")
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def row_one(rows: list[dict[str, str]], **filters: str) -> dict[str, str]:
    for row in rows:
        if all(str(row.get(key, "")) == str(value) for key, value in filters.items()):
            return row
    raise KeyError(f"missing row for filters={filters}")


def as_float(row: dict[str, str], key: str) -> float:
    return float(row[key])


def pct(value: float) -> float:
    return 100.0 * float(value)


def fmt_pct(value: float, digits: int = 1) -> str:
    return f"{pct(value):.{digits}f}%"


def fmt_pvalue(value: float) -> str:
    if value < 0.001:
        return "p<0.001"
    if value < 0.01:
        return f"p={value:.3f}"
    return f"p={value:.3g}"


def configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": "#30343A",
            "axes.linewidth": 0.8,
            "grid.color": "#D9DDE3",
            "grid.linewidth": 0.7,
            "grid.alpha": 0.8,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.dpi": 320,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def add_panel_label(ax, label: str) -> None:
    ax.text(
        -0.12,
        1.08,
        label,
        transform=ax.transAxes,
        fontsize=14,
        fontweight="bold",
        va="bottom",
        ha="left",
        color=PALETTE["black"],
    )


def wrap_text(text: str, width: int) -> str:
    return "\n".join(
        fill(line, width=width, break_long_words=False, break_on_hyphens=False) if line else ""
        for line in text.splitlines()
    )


def add_box(ax, x: float, y: float, w: float, h: float, text: str, face: str, edge: str, *, fontsize: float = 11) -> None:
    box = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        linewidth=1.3,
        facecolor=face,
        edgecolor=edge,
    )
    ax.add_patch(box)
    text_artist = ax.text(
        x + w / 2.0,
        y + h / 2.0,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=PALETTE["black"],
        linespacing=1.20,
    )
    text_artist.set_clip_path(box)


def add_metric_chip(ax, x: float, y: float, w: float, h: float, title: str, value: str, subtitle: str, face: str) -> None:
    chip = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.010,rounding_size=0.02",
        linewidth=0.9,
        facecolor=face,
        edgecolor=PALETTE["light_gray"],
    )
    ax.add_patch(chip)
    title_artist = ax.text(
        x + 0.04 * w,
        y + 0.80 * h,
        wrap_text(title, max(15, int(w * 105))),
        fontsize=8.8,
        fontweight="bold",
        ha="left",
        va="top",
        linespacing=1.10,
    )
    value_artist = ax.text(x + 0.04 * w, y + 0.44 * h, value, fontsize=14.5, fontweight="bold", ha="left", va="center")
    subtitle_artist = ax.text(
        x + 0.04 * w,
        y + 0.08 * h,
        wrap_text(subtitle, max(18, int(w * 138))),
        fontsize=7.8,
        color=PALETTE["dark_gray"],
        ha="left",
        va="bottom",
        linespacing=1.10,
    )
    title_artist.set_clip_path(chip)
    value_artist.set_clip_path(chip)
    subtitle_artist.set_clip_path(chip)


def add_arrow(ax, x1: float, y1: float, x2: float, y2: float, color: str = PALETTE["dark_gray"]) -> None:
    arrow = FancyArrowPatch(
        (x1, y1),
        (x2, y2),
        arrowstyle="-|>",
        mutation_scale=16,
        linewidth=1.4,
        color=color,
        connectionstyle="arc3,rad=0.0",
    )
    ax.add_patch(arrow)


def save_figure(fig, output_dir: Path, stem: str) -> dict[str, str]:
    png_path = output_dir / f"{stem}.png"
    pdf_path = output_dir / f"{stem}.pdf"
    fig.savefig(png_path, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)
    return {"png": str(png_path), "pdf": str(pdf_path)}


def draw_system_overview(
    *,
    output_dir: Path,
    method_rows: list[dict[str, str]],
    triage_rows: list[dict[str, str]],
) -> dict[str, str]:
    backbone_cross = row_one(
        method_rows,
        scenario_relation="cross",
        method="cpd_shift_multiproto_consensus_plus",
    )
    triage_cross = row_one(
        triage_rows,
        scenario_relation="cross",
        policy="triage_shift_multiproto_coverage_switch_plus_ova_nonbenign",
    )
    triage_same = row_one(
        triage_rows,
        scenario_relation="same",
        policy="triage_shift_multiproto_coverage_switch_plus_ova_nonbenign",
    )

    fig, ax = plt.subplots(figsize=(13.4, 7.8))
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.axis("off")

    ax.text(
        0.02,
        0.95,
        "Figure 1. OpenFedBot canonical deployment stack",
        fontsize=18,
        fontweight="bold",
        ha="left",
        va="top",
    )
    ax.text(
        0.02,
        0.905,
        "One safe auto backbone, one deployment operating policy, and one calibration policy tied to the canonical digest.",
        fontsize=10.5,
        color=PALETTE["dark_gray"],
        ha="left",
        va="top",
    )

    add_box(ax, 0.04, 0.57, 0.18, 0.18, "Federated source scenarios\nleave-one-family-out\nsame / cross protocols", PALETTE["soft_blue"], PALETTE["blue"], fontsize=10.8)
    add_box(ax, 0.27, 0.57, 0.18, 0.18, "Adaptive calibration bank\nmaximize cpd_val_coverage\ntie-break cpd_val_risk", PALETTE["soft_orange"], PALETTE["orange"], fontsize=10.5)
    add_box(ax, 0.50, 0.57, 0.20, 0.18, "Safe auto backbone\ncpd_shift_multiproto_\nconsensus_plus\nmulti-prototype + shift-aware reclaim", PALETTE["soft_blue"], PALETTE["blue"], fontsize=9.8)
    add_box(ax, 0.75, 0.57, 0.18, 0.18, "Deployment operating policy\ntriage_shift_multiproto_\ncoverage_switch_plus_\nova_nonbenign", PALETTE["soft_red"], PALETTE["vermillion"], fontsize=9.7)

    add_arrow(ax, 0.22, 0.66, 0.27, 0.66)
    add_arrow(ax, 0.45, 0.66, 0.50, 0.66)
    add_arrow(ax, 0.70, 0.66, 0.75, 0.66)

    ax.text(0.875, 0.44, "Deployment outputs", fontsize=9.8, fontweight="bold", ha="center", va="bottom", color=PALETTE["dark_gray"])
    add_box(ax, 0.81, 0.28, 0.13, 0.08, "Auto accept", "#F4F6F8", PALETTE["blue"], fontsize=10)
    add_box(ax, 0.81, 0.16, 0.13, 0.08, "Review queue", "#F4F6F8", PALETTE["orange"], fontsize=10)
    add_box(ax, 0.81, 0.04, 0.13, 0.08, "Final defer", "#F4F6F8", PALETTE["dark_gray"], fontsize=10)
    add_arrow(ax, 0.87, 0.57, 0.87, 0.36)
    add_arrow(ax, 0.875, 0.28, 0.875, 0.24)
    add_arrow(ax, 0.875, 0.16, 0.875, 0.12)

    add_metric_chip(ax, 0.05, 0.23, 0.18, 0.14, "Cross auto", fmt_pct(as_float(backbone_cross, "coverage_mean")), "safe backbone, not a high-automation headline", "#F8FBFE")
    add_metric_chip(ax, 0.26, 0.23, 0.18, 0.14, "Cross unknown misroute", fmt_pct(as_float(backbone_cross, "unknown_misroute_rate_mean"), digits=2), "supports the safety-first story", "#F8FBFE")
    add_metric_chip(ax, 0.47, 0.23, 0.20, 0.14, "Cross actionable", fmt_pct(as_float(triage_cross, "actionable_coverage_mean")), "after review recovery", "#FFF8F5")
    add_metric_chip(ax, 0.26, 0.06, 0.18, 0.14, "Review benign", fmt_pct(as_float(triage_cross, "review_benign_rate_mean"), digits=2), "keeps review burden controlled", "#FFF8F5")
    add_metric_chip(ax, 0.47, 0.06, 0.20, 0.14, "Cross safe unknown", fmt_pct(as_float(triage_cross, "safe_unknown_handling_rate_mean")), "same-scenario rises to " + fmt_pct(as_float(triage_same, "safe_unknown_handling_rate_mean")), "#FFF8F5")

    ax.text(0.04, 0.45, "WASA-facing hook:\nedge/cloud AI computing + smart networked applications\nAI-based network threat detection", fontsize=10.4, ha="left", va="top", color=PALETTE["dark_gray"], linespacing=1.35)
    ax.text(0.05, 0.02, "Frame the contribution as a deployment stack, not as a raw detector-versus-detector headline.", fontsize=9.1, ha="left", va="bottom", color=PALETTE["dark_gray"])

    return save_figure(fig, output_dir, "fig1_openfedbot_system_overview")


def draw_auto_scatter(ax, rows: list[dict[str, str]], relation: str) -> None:
    methods = [
        "cpd_shift_multiproto_consensus_plus",
        "cpd_shift_consensus_plus",
        "cpd_shift_multiproto_coverage_switch_plus",
        "ova_gate",
        "msp",
        "energy",
    ]
    for method in methods:
        row = row_one(rows, scenario_relation=relation, method=method)
        x = pct(as_float(row, "coverage_mean"))
        y = pct(1.0 - as_float(row, "unknown_misroute_rate_mean"))
        color = METHOD_COLORS[method]
        marker = METHOD_MARKERS[method]
        size = 140 if method == "cpd_shift_multiproto_consensus_plus" else 110
        edge = PALETTE["black"] if method == "cpd_shift_multiproto_consensus_plus" else "white"
        ax.scatter(x, y, s=size, marker=marker, color=color, edgecolor=edge, linewidth=1.0, zorder=3)
        dx, dy, ha, va = SCATTER_LABEL_OFFSETS[relation][method]
        ax.annotate(
            SCATTER_LABELS[method],
            xy=(x, y),
            xytext=(x + dx, y + dy),
            textcoords="data",
            fontsize=7.6,
            ha=ha,
            va=va,
            color=PALETTE["dark_gray"],
            bbox={"boxstyle": "round,pad=0.10", "facecolor": "white", "edgecolor": "none", "alpha": 0.78},
            arrowprops={
                "arrowstyle": "-",
                "linewidth": 0.8,
                "color": "#B8BFC7",
                "shrinkA": 4,
                "shrinkB": 4,
            },
            zorder=4,
        )

    ax.set_title(f"{relation.capitalize()} automatic operating plane")
    ax.set_xlabel("Automatic coverage (%)")
    ax.set_ylabel("Safe unknown handling (%)")
    ax.grid(True, axis="both")
    ax.set_xlim(0, 74)
    ax.set_ylim(39.5, 101.0)


def draw_forest(ax, rows: list[dict[str, str]], title: str) -> None:
    ordered = [row_one(rows, metric=metric) for metric in FOREST_METRICS]
    y_positions = np.arange(len(ordered))[::-1]
    x_values = np.array([pct(as_float(row, "mean_protocol_benefit_for_reference")) for row in ordered], dtype=np.float64)
    ci_low = np.array([pct(as_float(row, "bootstrap_ci_low")) for row in ordered], dtype=np.float64)
    ci_high = np.array([pct(as_float(row, "bootstrap_ci_high")) for row in ordered], dtype=np.float64)
    xerr = np.vstack([x_values - ci_low, ci_high - x_values])
    pvalues = [as_float(row, "sign_test_pvalue") for row in ordered]

    ax.axvline(0.0, color=PALETTE["dark_gray"], linestyle="--", linewidth=1.0, zorder=1)
    for idx, (x, y, pv) in enumerate(zip(x_values, y_positions, pvalues)):
        face = METHOD_COLORS["cpd_shift_multiproto_consensus_plus"] if pv < 0.05 else "white"
        ax.errorbar(
            x,
            y,
            xerr=np.array([[xerr[0, idx]], [xerr[1, idx]]]),
            fmt="o",
            color=METHOD_COLORS["cpd_shift_multiproto_consensus_plus"],
            markerfacecolor=face,
            markeredgecolor=METHOD_COLORS["cpd_shift_multiproto_consensus_plus"],
            linewidth=1.5,
            markersize=7,
            capsize=4,
            zorder=3,
        )
        ax.text(max(ci_high.max(), 0.0) + 0.8, y, fmt_pvalue(pv), fontsize=8.5, va="center", ha="left", color=PALETTE["dark_gray"])

    ax.set_yticks(y_positions)
    ax.set_yticklabels([FOREST_LABELS[row["metric"]] for row in ordered])
    ax.set_title(title)
    ax.set_xlabel("Benefit for multiproto backbone (percentage points)")
    ax.grid(True, axis="x")
    ax.set_xlim(min(ci_low.min(), 0.0) - 1.0, max(ci_high.max(), 0.0) + 4.4)
    ax.set_ylim(-0.7, len(ordered) - 0.3)
    ax.text(0.01, 0.03, "filled marker: sign test p < 0.05", transform=ax.transAxes, fontsize=8.4, color=PALETTE["dark_gray"], ha="left", va="bottom")


def draw_safe_auto_figure(
    *,
    output_dir: Path,
    method_rows: list[dict[str, str]],
    paired_vs_old: list[dict[str, str]],
    paired_vs_covswitch: list[dict[str, str]],
) -> dict[str, str]:
    fig = plt.figure(figsize=(13.2, 10.6))
    axes = fig.subplot_mosaic([["A", "B"], ["C", "D"]], gridspec_kw={"hspace": 0.34, "wspace": 0.28})

    draw_auto_scatter(axes["A"], method_rows, "cross")
    add_panel_label(axes["A"], "A")
    draw_auto_scatter(axes["B"], method_rows, "same")
    add_panel_label(axes["B"], "B")
    draw_forest(axes["C"], paired_vs_old, "Backbone vs older shift-consensus line")
    add_panel_label(axes["C"], "C")
    draw_forest(axes["D"], paired_vs_covswitch, "Backbone vs aggressive coverage-switch auto line")
    add_panel_label(axes["D"], "D")

    fig.suptitle(
        "Figure 2. Why the paper mainline should keep a safe automatic backbone",
        fontsize=17,
        fontweight="bold",
        x=0.04,
        y=0.995,
        ha="left",
    )
    fig.text(
        0.04,
        0.965,
        "Good papers usually separate the main systems claim from the aggressive operating point. This figure keeps the backbone, the baselines, and the paired evidence in one compact compound figure.",
        fontsize=10.5,
        color=PALETTE["dark_gray"],
        ha="left",
    )

    return save_figure(fig, output_dir, "fig2_safe_auto_backbone_evidence")


def draw_deployment_breakdown(ax, row_cross: dict[str, str], row_same: dict[str, str]) -> None:
    labels = ["Cross", "Same"]
    auto = np.array([pct(as_float(row_cross, "auto_coverage_mean")), pct(as_float(row_same, "auto_coverage_mean"))])
    review = np.array([pct(as_float(row_cross, "review_coverage_mean")), pct(as_float(row_same, "review_coverage_mean"))])
    defer = np.array([pct(as_float(row_cross, "final_defer_rate_mean")), pct(as_float(row_same, "final_defer_rate_mean"))])
    x = np.arange(2)

    ax.bar(x, auto, color=PALETTE["blue"], label="Auto coverage")
    ax.bar(x, review, bottom=auto, color=PALETTE["orange"], label="Review coverage")
    ax.bar(x, defer, bottom=auto + review, color=PALETTE["light_gray"], label="Final defer")

    for idx, (a, r, d) in enumerate(zip(auto, review, defer)):
        ax.text(idx, a / 2.0, f"{a:.1f}", ha="center", va="center", fontsize=9, color="white", fontweight="bold")
        ax.text(idx, a + r / 2.0, f"{r:.1f}", ha="center", va="center", fontsize=9, color=PALETTE["black"], fontweight="bold")
        ax.text(idx, a + r + d / 2.0, f"{d:.1f}", ha="center", va="center", fontsize=9, color=PALETTE["dark_gray"])

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Target flows (%)")
    ax.set_title("Main policy resolves work through auto + review")
    ax.set_ylim(0, 100)
    ax.legend(loc="upper right", frameon=False)
    ax.grid(True, axis="y")


def draw_cost_bubble(ax, row_cross: dict[str, str], row_same: dict[str, str]) -> None:
    data = [
        ("Cross", row_cross, PALETTE["vermillion"]),
        ("Same", row_same, PALETTE["blue"]),
    ]
    for label, row, color in data:
        x = as_float(row, "actionable_nodes_per_sec_mean")
        y = as_float(row, "review_queue_per_1k_targets_mean")
        size = 2.5 * as_float(row, "defer_queue_per_1k_targets_mean")
        ax.scatter(x, y, s=size, color=color, alpha=0.55, edgecolor="white", linewidth=1.4)
        ax.text(
            x + 45,
            y + 5,
            f"{label}\nreview {y:.0f}/1k\n"
            f"defer {as_float(row, 'defer_queue_per_1k_targets_mean'):.0f}/1k",
            fontsize=9,
            ha="left",
            va="bottom",
            color=PALETTE["dark_gray"],
        )

    ax.set_title("Deployment cost map")
    ax.set_xlabel("Actionable nodes per second")
    ax.set_ylabel("Review queue per 1k targets")
    ax.grid(True, axis="both")
    ax.text(0.02, 0.03, "Bubble area ∝ final defer queue per 1k targets", transform=ax.transAxes, fontsize=8.5, color=PALETTE["dark_gray"], ha="left", va="bottom")


def draw_grouped_protocol_bars(
    ax,
    rows: list[dict[str, str]],
    *,
    protocols: list[str],
    metric_defs: list[tuple[str, str, callable]],
    title: str,
) -> None:
    width = 0.22
    x = np.arange(len(protocols), dtype=np.float64)
    metric_colors = [PALETTE["blue"], PALETTE["purple"], PALETTE["green"], PALETTE["orange"]]

    for metric_idx, (_, label, transform) in enumerate(metric_defs):
        values = np.array([pct(transform(row_one(rows, protocol=protocol))) for protocol in protocols], dtype=np.float64)
        positions = x + (metric_idx - (len(metric_defs) - 1) / 2.0) * width
        ax.bar(positions, values, width=width, color=metric_colors[metric_idx], label=label)
        for pos, value in zip(positions, values):
            ax.text(pos, value + 1.0, f"{value:.1f}", ha="center", va="bottom", fontsize=8, rotation=90)

    ax.set_xticks(x)
    ax.set_xticklabels([PROTOCOL_LABELS.get(protocol, protocol) for protocol in protocols], rotation=18, ha="right")
    ax.set_ylim(0, 104)
    ax.set_ylabel("Score (%)")
    ax.set_title(title)
    ax.grid(True, axis="y")
    ax.legend(loc="upper right", frameon=False)


def draw_deployment_figure(
    *,
    output_dir: Path,
    triage_rows: list[dict[str, str]],
    deployment_rows: list[dict[str, str]],
    hardest_auto_rows: list[dict[str, str]],
    hardest_triage_rows: list[dict[str, str]],
) -> dict[str, str]:
    triage_cross = row_one(triage_rows, scenario_relation="cross", policy="triage_shift_multiproto_coverage_switch_plus_ova_nonbenign")
    triage_same = row_one(triage_rows, scenario_relation="same", policy="triage_shift_multiproto_coverage_switch_plus_ova_nonbenign")
    deployment_cross = row_one(deployment_rows, scenario_relation="cross", policy="triage_shift_multiproto_coverage_switch_plus_ova_nonbenign")
    deployment_same = row_one(deployment_rows, scenario_relation="same", policy="triage_shift_multiproto_coverage_switch_plus_ova_nonbenign")

    top_cross_protocols = [
        row["protocol"]
        for row in hardest_auto_rows
        if row["scenario_relation"] == "cross" and int(float(row["rank_within_relation"])) <= 3
    ]

    fig = plt.figure(figsize=(13.2, 10.6))
    axes = fig.subplot_mosaic([["A", "B"], ["C", "D"]], gridspec_kw={"hspace": 0.36, "wspace": 0.30})

    draw_deployment_breakdown(axes["A"], triage_cross, triage_same)
    add_panel_label(axes["A"], "A")
    draw_cost_bubble(axes["B"], deployment_cross, deployment_same)
    add_panel_label(axes["B"], "B")
    draw_grouped_protocol_bars(
        axes["C"],
        hardest_auto_rows,
        protocols=top_cross_protocols,
        metric_defs=[
            ("coverage_mean", "Coverage", lambda row: as_float(row, "coverage_mean")),
            ("selective_risk_mean", "Accepted precision", lambda row: 1.0 - as_float(row, "selective_risk_mean")),
            ("unknown_misroute_rate_mean", "Safe unknown", lambda row: 1.0 - as_float(row, "unknown_misroute_rate_mean")),
        ],
        title="Hardest cross protocols: automatic stage quality triplet",
    )
    add_panel_label(axes["C"], "C")
    draw_grouped_protocol_bars(
        axes["D"],
        hardest_triage_rows,
        protocols=top_cross_protocols,
        metric_defs=[
            ("actionable_coverage_mean", "Actionable coverage", lambda row: as_float(row, "actionable_coverage_mean")),
            ("review_coverage_mean", "Review coverage", lambda row: as_float(row, "review_coverage_mean")),
            ("safe_unknown_handling_rate_mean", "Safe unknown", lambda row: as_float(row, "safe_unknown_handling_rate_mean")),
        ],
        title="Hardest cross protocols: triage recovers deployment usability",
    )
    add_panel_label(axes["D"], "D")

    fig.suptitle(
        "Figure 3. Deployment value comes from workload shaping, not from pretending automation is solved",
        fontsize=17,
        fontweight="bold",
        x=0.04,
        y=0.995,
        ha="left",
    )
    fig.text(
        0.04,
        0.965,
        "The stronger paper figure is the one that puts coverage recovery, review burden, cost, and hardest-protocol behavior in the same compound view.",
        fontsize=10.5,
        color=PALETTE["dark_gray"],
        ha="left",
    )

    return save_figure(fig, output_dir, "fig3_deployment_and_hardest_protocols")


def draw_threshold_figure(
    *,
    output_dir: Path,
    cov10_rows: list[dict[str, str]],
    cov12_rows: list[dict[str, str]],
    cov14_rows: list[dict[str, str]],
) -> dict[str, str]:
    ordered = [
        (0.10, row_one(cov10_rows, scenario_relation="cross", policy="triage_shift_multiproto_coverage_switch_plus_ova_nonbenign"), row_one(cov10_rows, scenario_relation="same", policy="triage_shift_multiproto_coverage_switch_plus_ova_nonbenign")),
        (0.12, row_one(cov12_rows, scenario_relation="cross", policy="triage_shift_multiproto_coverage_switch_plus_ova_nonbenign"), row_one(cov12_rows, scenario_relation="same", policy="triage_shift_multiproto_coverage_switch_plus_ova_nonbenign")),
        (0.14, row_one(cov14_rows, scenario_relation="cross", policy="triage_shift_multiproto_coverage_switch_plus_ova_nonbenign"), row_one(cov14_rows, scenario_relation="same", policy="triage_shift_multiproto_coverage_switch_plus_ova_nonbenign")),
    ]
    thresholds = np.array([item[0] for item in ordered], dtype=np.float64)
    cross_actionable = np.array([pct(as_float(item[1], "actionable_coverage_mean")) for item in ordered], dtype=np.float64)
    cross_safe = np.array([pct(as_float(item[1], "safe_unknown_handling_rate_mean")) for item in ordered], dtype=np.float64)
    same_actionable = np.array([pct(as_float(item[2], "actionable_coverage_mean")) for item in ordered], dtype=np.float64)

    fig = plt.figure(figsize=(13.2, 9.8))
    axes = fig.subplot_mosaic([["A", "B"], ["C", "D"]], gridspec_kw={"hspace": 0.38, "wspace": 0.28})

    ax = axes["A"]
    for threshold, x, y in zip(thresholds, cross_safe, cross_actionable):
        ax.scatter(x, y, s=180, color=THRESHOLD_COLORS[float(threshold)], edgecolor="white", linewidth=1.6, zorder=3)
        ax.text(x + 0.2, y + 0.08, f"{threshold:.2f}", fontsize=9.5, color=PALETTE["dark_gray"])
    ax.plot(cross_safe, cross_actionable, color=PALETTE["dark_gray"], linewidth=1.2, alpha=0.8)
    ax.scatter(cross_safe[1], cross_actionable[1], s=300, facecolor="none", edgecolor=PALETTE["black"], linewidth=1.3, zorder=4)
    ax.set_title("Cross-scenario threshold tradeoff")
    ax.set_xlabel("Safe unknown handling (%)")
    ax.set_ylabel("Actionable coverage (%)")
    ax.grid(True, axis="both")
    add_panel_label(ax, "A")

    ax = axes["B"]
    ax.plot(thresholds, cross_actionable, color=PALETTE["blue"], marker="o", linewidth=2.2)
    ax.axvline(0.12, color=PALETTE["dark_gray"], linestyle="--", linewidth=1.0)
    ax.set_title("Cross actionable coverage")
    ax.set_xlabel("Coverage-switch activation threshold")
    ax.set_ylabel("Actionable coverage (%)")
    ax.grid(True, axis="y")
    add_panel_label(ax, "B")

    ax = axes["C"]
    ax.plot(thresholds, cross_safe, color=PALETTE["vermillion"], marker="o", linewidth=2.2)
    ax.axvline(0.12, color=PALETTE["dark_gray"], linestyle="--", linewidth=1.0)
    ax.set_title("Cross safe unknown handling")
    ax.set_xlabel("Coverage-switch activation threshold")
    ax.set_ylabel("Safe unknown handling (%)")
    ax.grid(True, axis="y")
    add_panel_label(ax, "C")

    ax = axes["D"]
    ax.plot(thresholds, same_actionable, color=PALETTE["green"], marker="o", linewidth=2.2)
    ax.axvline(0.12, color=PALETTE["dark_gray"], linestyle="--", linewidth=1.0)
    ax.set_title("Same-scenario actionable coverage")
    ax.set_xlabel("Coverage-switch activation threshold")
    ax.set_ylabel("Actionable coverage (%)")
    ax.grid(True, axis="y")
    add_panel_label(ax, "D")

    fig.suptitle(
        "Figure 4. The threshold choice should be justified by the tradeoff surface, not by a tiny coverage gain in isolation",
        fontsize=17,
        fontweight="bold",
        x=0.04,
        y=0.995,
        ha="left",
    )
    fig.text(
        0.04,
        0.965,
        "Good papers often dedicate one full figure to the operating-point decision. Here, 0.12 stays canonical because 0.14 buys too little coverage for a visible safety drop.",
        fontsize=10.5,
        color=PALETTE["dark_gray"],
        ha="left",
    )

    return save_figure(fig, output_dir, "fig4_threshold_selection")


def main() -> None:
    configure_matplotlib()
    args = parse_args()

    digest_dir = (PROJECT_ROOT / str(args.digest_dir)).resolve()
    cov10_dir = (PROJECT_ROOT / str(args.cov10_digest_dir)).resolve()
    cov14_dir = (PROJECT_ROOT / str(args.cov14_digest_dir)).resolve()
    output_root = (PROJECT_ROOT / str(args.output_root)).resolve()
    output_dir = ensure_dir(output_root / f"wasa_main_figures_{timestamp_utc()}")

    method_rows = read_rows(digest_dir / "paper_main_method_summary.csv")
    triage_rows = read_rows(digest_dir / "paper_main_triage_summary.csv")
    deployment_rows = read_rows(digest_dir / "paper_deployment_summary.csv")
    hardest_auto_rows = read_rows(digest_dir / "hardest_cpd_consensus_protocols.csv")
    hardest_triage_rows = read_rows(digest_dir / "hardest_triage_consensus_ova_protocols.csv")
    cov10_rows = read_rows(cov10_dir / "paper_main_triage_summary.csv")
    cov12_rows = triage_rows
    cov14_rows = read_rows(cov14_dir / "paper_main_triage_summary.csv")
    paired_vs_old = read_rows(digest_dir / "adaptive_paired_cpd_shift_multiproto_consensus_plus_vs_cpd_shift_consensus_plus_summary.csv")
    paired_vs_covswitch = read_rows(digest_dir / "adaptive_paired_cpd_shift_multiproto_consensus_plus_vs_cpd_shift_multiproto_coverage_switch_plus_summary.csv")

    outputs = {
        "figure_1": {
            "title": "OpenFedBot canonical deployment stack",
            "takeaway": "One conservative automatic backbone plus one deployment operating policy.",
            **draw_system_overview(output_dir=output_dir, method_rows=method_rows, triage_rows=triage_rows),
        },
        "figure_2": {
            "title": "Safe automatic backbone evidence",
            "takeaway": "The multiproto line is a backbone, not a high-automation headline.",
            **draw_safe_auto_figure(output_dir=output_dir, method_rows=method_rows, paired_vs_old=paired_vs_old, paired_vs_covswitch=paired_vs_covswitch),
        },
        "figure_3": {
            "title": "Deployment value and hardest protocols",
            "takeaway": "Review recovery and cost shaping make the deployment story work.",
            **draw_deployment_figure(output_dir=output_dir, triage_rows=triage_rows, deployment_rows=deployment_rows, hardest_auto_rows=hardest_auto_rows, hardest_triage_rows=hardest_triage_rows),
        },
        "figure_4": {
            "title": "Threshold selection",
            "takeaway": "0.12 remains the canonical operating point after sweep.",
            **draw_threshold_figure(output_dir=output_dir, cov10_rows=cov10_rows, cov12_rows=cov12_rows, cov14_rows=cov14_rows),
        },
    }

    save_json(
        output_dir / "figure_manifest.json",
        {
            "output_dir": str(output_dir),
            "digest_dir": str(digest_dir),
            "cov10_digest_dir": str(cov10_dir),
            "cov14_digest_dir": str(cov14_dir),
            "figures": outputs,
        },
    )
    print(str(output_dir))


if __name__ == "__main__":
    main()
