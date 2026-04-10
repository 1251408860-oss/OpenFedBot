#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import torch

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from openfedbot.common import ensure_dir, save_json, timestamp_utc
from openfedbot.schema import GRAPH_SCHEMA_VERSION, load_validated_graph_bundle


SCENARIOS = {
    "scenario_e": {
        "source_dir": "mininet_testbed/real_collection/scenario_e_three_tier_high2",
        "graph_name": "cabench_scenario_e_three_tier_high2_public_graph.pt",
        "manifest_name": "cabench_scenario_e_three_tier_high2_public_manifest.json",
    },
    "scenario_h": {
        "source_dir": "mininet_testbed/real_collection/scenario_h_mimic_heavy_overlap",
        "graph_name": "cabench_scenario_h_mimic_heavy_overlap_public_graph.pt",
        "manifest_name": "cabench_scenario_h_mimic_heavy_overlap_public_manifest.json",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build OpenFedBot-ready public graphs from a Ca-Bench checkout")
    parser.add_argument("--cabench-root", required=True)
    parser.add_argument("--output-root", default="assets/public_cabench_v1")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--scenarios", nargs="*", default=["scenario_e", "scenario_h"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--delta-t", type=float, default=1.0)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def repo_path(value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (PROJECT_ROOT / path).resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_graph(
    *,
    python_bin: str,
    builder_script: Path,
    source_pcap: Path,
    source_manifest: Path,
    output_graph: Path,
    output_manifest: Path,
    seed: int,
    delta_t: float,
) -> None:
    ensure_dir(output_graph.parent)
    ensure_dir(output_manifest.parent)
    subprocess.run(
        [
            python_bin,
            str(builder_script),
            "--pcap-file",
            str(source_pcap),
            "--manifest-file",
            str(source_manifest),
            "--output-file",
            str(output_graph),
            "--seed",
            str(seed),
            "--delta-t",
            str(delta_t),
        ],
        check=True,
        cwd=str(builder_script.parent),
    )
    shutil.copy2(source_manifest, output_manifest)

    graph = torch.load(output_graph, weights_only=False, map_location="cpu")
    graph.graph_schema_version = GRAPH_SCHEMA_VERSION
    graph.manifest_file = str(output_manifest.resolve())
    graph.public_asset_source = "Ca-Bench public collection"
    torch.save(graph, output_graph)


def summarize_asset(
    *,
    scenario_name: str,
    output_graph: Path,
    output_manifest: Path,
    source_pcap: Path,
    source_manifest: Path,
    reused_existing: bool,
) -> dict[str, object]:
    _, _, report = load_validated_graph_bundle(
        graph_path=output_graph,
        manifest_path=output_manifest,
    )
    return {
        "scenario_name": scenario_name,
        "reused_existing": bool(reused_existing),
        "source_pcap": str(source_pcap.resolve()),
        "source_manifest": str(source_manifest.resolve()),
        "output_graph": str(output_graph.resolve()),
        "output_manifest": str(output_manifest.resolve()),
        "source_pcap_sha256": sha256_file(source_pcap),
        "source_manifest_sha256": sha256_file(source_manifest),
        "output_graph_sha256": sha256_file(output_graph),
        "output_manifest_sha256": sha256_file(output_manifest),
        "num_nodes": report.num_nodes,
        "num_edges": report.num_edges,
        "num_features": report.num_features,
        "source_ip_count": report.source_ip_count,
        "graph_schema_version": GRAPH_SCHEMA_VERSION,
        "warnings": report.warnings,
    }


def main() -> None:
    args = parse_args()
    cabench_root = repo_path(args.cabench_root)
    output_root = repo_path(args.output_root)
    builder_script = PROJECT_ROOT / "third_party" / "cabench_frozen" / "core_experiments" / "build_graph_v2.py"

    if not cabench_root.exists():
        raise SystemExit(f"Ca-Bench root not found: {cabench_root}")
    if not builder_script.exists():
        raise SystemExit(f"Frozen builder not found: {builder_script}")

    scenario_names = [str(item) for item in list(args.scenarios)]
    unknown = [name for name in scenario_names if name not in SCENARIOS]
    if unknown:
        raise SystemExit(f"Unknown scenarios: {', '.join(unknown)}")

    records: list[dict[str, object]] = []
    for scenario_name in scenario_names:
        spec = SCENARIOS[scenario_name]
        source_dir = cabench_root / str(spec["source_dir"])
        source_pcap = source_dir / "full_arena_v2.pcap"
        source_manifest = source_dir / "arena_manifest_v2.json"
        output_graph = output_root / "graphs" / str(spec["graph_name"])
        output_manifest = output_root / "meta" / str(spec["manifest_name"])

        if not source_pcap.exists():
            raise SystemExit(f"Missing source PCAP for {scenario_name}: {source_pcap}")
        if not source_manifest.exists():
            raise SystemExit(f"Missing source manifest for {scenario_name}: {source_manifest}")

        reused_existing = output_graph.exists() and output_manifest.exists() and not bool(args.force)
        if not reused_existing:
            build_graph(
                python_bin=str(args.python),
                builder_script=builder_script,
                source_pcap=source_pcap,
                source_manifest=source_manifest,
                output_graph=output_graph,
                output_manifest=output_manifest,
                seed=int(args.seed),
                delta_t=float(args.delta_t),
            )

        records.append(
            summarize_asset(
                scenario_name=scenario_name,
                output_graph=output_graph,
                output_manifest=output_manifest,
                source_pcap=source_pcap,
                source_manifest=source_manifest,
                reused_existing=reused_existing,
            )
        )

    manifest = {
        "created_at_utc": timestamp_utc(),
        "cabench_root": str(cabench_root),
        "output_root": str(output_root),
        "builder_script": str(builder_script),
        "records": records,
    }
    save_json(output_root / "asset_manifest.json", manifest)
    print(str(output_root))


if __name__ == "__main__":
    main()
