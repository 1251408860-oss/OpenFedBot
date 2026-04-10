#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from openfedbot.common import ensure_dir, load_json, save_json, timestamp_utc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a stable paper-facing submission bundle")
    parser.add_argument("--authoritative-manifest", required=True)
    parser.add_argument("--output-root", default="results")
    parser.add_argument("--paper-draft", default="docs/wasa_paper_draft_20260409.md")
    parser.add_argument("--playbook", default="docs/repro_submission_playbook_20260409.md")
    parser.add_argument("--submission-packet", default="docs/wasa_submission_packet_20260409.md")
    parser.add_argument("--experiment-note", default="docs/wasa_submission_convergence_20260408.md")
    parser.add_argument("--include", nargs="*", default=[])
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


def copy_file(src: Path, dest_root: Path, relative_dest: str) -> dict[str, object]:
    dest = dest_root / relative_dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return {
        "source": str(src),
        "bundle_path": str(dest),
        "size_bytes": src.stat().st_size,
        "sha256": sha256_file(src),
    }


def add_if_exists(records: list[dict[str, object]], src: Path, dest_root: Path, relative_dest: str) -> None:
    if src.exists():
        records.append(copy_file(src, dest_root, relative_dest))


def main() -> None:
    args = parse_args()
    authoritative_manifest_path = repo_path(args.authoritative_manifest)
    authoritative_manifest = load_json(authoritative_manifest_path)
    digest_dir = authoritative_manifest_path.parent
    run_manifest_path = digest_dir / "manifest.json"
    run_manifest = load_json(run_manifest_path) if run_manifest_path.exists() else {}

    output_root = repo_path(args.output_root)
    bundle_dir = ensure_dir(output_root / f"submission_bundle_{timestamp_utc()}")
    ensure_dir(bundle_dir / "tables")
    ensure_dir(bundle_dir / "figures")
    ensure_dir(bundle_dir / "docs")
    ensure_dir(bundle_dir / "manifests")
    ensure_dir(bundle_dir / "scripts")
    ensure_dir(bundle_dir / "configs")

    records: list[dict[str, object]] = []

    authoritative_outputs = dict(authoritative_manifest.get("authoritative_outputs", {}))
    for _, raw_path in authoritative_outputs.items():
        src = repo_path(str(raw_path))
        suffix = src.suffix.lower()
        if suffix == ".png":
            relative_dest = f"figures/{src.name}"
        else:
            relative_dest = f"tables/{src.name}"
        records.append(copy_file(src, bundle_dir, relative_dest))

    records.append(copy_file(authoritative_manifest_path, bundle_dir, f"manifests/{authoritative_manifest_path.name}"))
    if run_manifest_path.exists():
        records.append(copy_file(run_manifest_path, bundle_dir, f"manifests/{run_manifest_path.name}"))

    optional_docs = [
        args.paper_draft,
        args.playbook,
        args.submission_packet,
        args.experiment_note,
    ]
    for raw_path in optional_docs:
        if str(raw_path).strip():
            src = repo_path(str(raw_path))
            add_if_exists(records, src, bundle_dir, f"docs/{src.name}")

    default_docs = [
        (PROJECT_ROOT / "README.md", "docs/README.md"),
        (PROJECT_ROOT / "docs" / "graph_schema_contract_v1.md", "docs/graph_schema_contract_v1.md"),
        (PROJECT_ROOT / "third_party" / "cabench_frozen" / "README.md", "docs/cabench_frozen_README.md"),
    ]
    for src, relative_dest in default_docs:
        add_if_exists(records, src, bundle_dir, relative_dest)

    default_scripts = [
        PROJECT_ROOT / "scripts" / "build_reinforced_digest.py",
        PROJECT_ROOT / "scripts" / "build_submission_bundle.py",
        PROJECT_ROOT / "scripts" / "validate_graph_schema.py",
    ]
    for src in default_scripts:
        add_if_exists(records, src, bundle_dir, f"scripts/{src.name}")

    default_configs = [
        PROJECT_ROOT / "configs" / "open_world_full_suite_multiproto_coverageswitch_clean_seed10.json",
    ]
    for src in default_configs:
        add_if_exists(records, src, bundle_dir, f"configs/{src.name}")

    for raw_path in list(args.include):
        src = repo_path(str(raw_path))
        if src.is_dir():
            continue
        add_if_exists(records, src, bundle_dir, f"docs/{src.name}")

    bundle_manifest = {
        "bundle_dir": str(bundle_dir),
        "source_authoritative_manifest": str(authoritative_manifest_path),
        "source_run_manifest": str(run_manifest_path) if run_manifest_path.exists() else "",
        "source_run_dir": str(run_manifest.get("run_dir", "")),
        "source_digest_dir": str(run_manifest.get("digest_dir", str(digest_dir))),
        "paper_main_method": authoritative_manifest.get("paper_main_method", ""),
        "paper_main_policy": authoritative_manifest.get("paper_main_policy", ""),
        "records": records,
    }
    save_json(bundle_dir / "bundle_manifest.json", bundle_manifest)
    print(str(bundle_dir))


if __name__ == "__main__":
    main()
