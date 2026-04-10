#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from openfedbot.common import load_json
from openfedbot.schema import GRAPH_SCHEMA_VERSION, load_validated_graph_bundle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate OpenFedBot graph schema compatibility")
    parser.add_argument("--graph", default="")
    parser.add_argument("--manifest", default="")
    parser.add_argument("--config", default="")
    parser.add_argument("--graph-root", default="")
    return parser.parse_args()


def repo_path(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return (root / path).resolve()


def input_root(cfg: dict[str, object], override_root: str = "") -> Path:
    if str(override_root).strip():
        return repo_path(PROJECT_ROOT, str(override_root))
    if cfg.get("graph_root") is not None:
        return repo_path(PROJECT_ROOT, str(cfg["graph_root"]))
    if cfg.get("hitrust_root") is not None:
        return repo_path(PROJECT_ROOT, str(cfg["hitrust_root"]))
    return PROJECT_ROOT


def resolve_scenario_spec(root: Path, raw_value: object) -> tuple[Path, Path | None]:
    if isinstance(raw_value, str):
        return repo_path(root, raw_value), None
    item = dict(raw_value)
    graph_path = repo_path(root, str(item["graph_path"]))
    manifest_path = None
    if item.get("manifest_path") is not None:
        manifest_path = repo_path(root, str(item["manifest_path"]))
    return graph_path, manifest_path


def validate_one(graph_path: Path, manifest_path: Path | None) -> dict[str, object]:
    _, _, report = load_validated_graph_bundle(
        graph_path=graph_path,
        manifest_path=manifest_path,
    )
    return {
        "graph_path": str(report.graph_path),
        "manifest_path": str(report.manifest_path) if report.manifest_path is not None else "",
        "expected_graph_schema_version": GRAPH_SCHEMA_VERSION,
        "observed_graph_schema_version": report.observed_schema_version,
        "num_nodes": report.num_nodes,
        "num_edges": report.num_edges,
        "num_features": report.num_features,
        "source_ip_count": report.source_ip_count,
        "warnings": report.warnings,
    }


def main() -> None:
    args = parse_args()
    outputs: list[dict[str, object]] = []

    if str(args.config).strip():
        cfg = load_json(args.config)
        root = input_root(cfg, args.graph_root)
        for scenario_name, raw_value in dict(cfg["scenario_graphs"]).items():
            graph_path, manifest_path = resolve_scenario_spec(root, raw_value)
            item = validate_one(graph_path, manifest_path)
            item["scenario_name"] = str(scenario_name)
            outputs.append(item)
    else:
        if not str(args.graph).strip():
            raise SystemExit("Either --config or --graph must be provided")
        graph_path = repo_path(PROJECT_ROOT, str(args.graph))
        manifest_path = repo_path(PROJECT_ROOT, str(args.manifest)) if str(args.manifest).strip() else None
        outputs.append(validate_one(graph_path, manifest_path))

    print(json.dumps(outputs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
