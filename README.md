# OpenFedBot: Reviewer-Facing Open-World Federated Bot Triage

This repository contains the anonymous implementation and paper artifact package for `OpenFedBot`, a deployment-oriented open-world federated bot triage system on graph data.

To keep the review path short, the package is organized into a small set of reviewer-facing modules. Reviewers may inspect the tracked paper bundle directly, or rebuild the smoke and mainline experiments from the public `Ca-Bench` packet captures.

## Repository Navigation & Artifact Mapping

| Scope | Description | Directory Link |
| :--- | :--- | :--- |
| Core implementation | Training, calibration, metrics, schema validation, reporting, and triage logic | [`openfedbot`](./openfedbot) |
| Experiment entrypoints | Public-graph preparation, experiment execution, digest rebuild, bundle rebuild, and figure generation | [`scripts`](./scripts) |
| Runnable configs | Maintained experiment configs used by the smoke path, mainline, and coverage ablations | [`configs`](./configs) |
| Tracked paper artifact package | Reviewer-sized bundle mirrored from the active workspace | [`paper_artifacts`](./paper_artifacts) |
| Reproduction guide | Step-by-step reviewer reproduction commands and expected outputs | [`repro/README.md`](./repro/README.md) |
| Active docs | Graph schema plus current paper-facing notes | [`docs`](./docs) |
| Frozen builder provenance | Vendored `Ca-Bench` graph builder snapshot used for public graph construction | [`third_party/cabench_frozen`](./third_party/cabench_frozen) |
| Local runtime assets | Reviewer-local graph assets generated from public `Ca-Bench` data | [`assets`](./assets) |
| Local generated outputs | Non-tracked local runs, digests, bundles, figures, and archived workspace artifacts | [`results`](./results) |

## Reviewer Fast Path

If you only want the paper-facing outputs, start here:

1. [`paper_artifacts/README.md`](./paper_artifacts/README.md)
2. [`paper_artifacts/submission_bundle_20260409/`](./paper_artifacts/submission_bundle_20260409/)
3. [`paper_artifacts/submission_bundle_20260409/tables/`](./paper_artifacts/submission_bundle_20260409/tables/)
4. [`paper_artifacts/submission_bundle_20260409/figures/`](./paper_artifacts/submission_bundle_20260409/figures/)
5. [`paper_artifacts/submission_bundle_20260409/docs/`](./paper_artifacts/submission_bundle_20260409/docs/)

## Global Environment Overview

The maintained evaluation path targets Ubuntu/Linux with Python `3.10`.

The repository was rerun successfully on `2026-04-10` in a matching `DL` environment with:

- Python `3.10.19`
- numpy `2.2.6`
- scipy `1.15.3`
- matplotlib `3.10.8`
- scikit-learn `1.7.2`
- torch `2.10.0` (`2.10.0+cu128` in the original local environment)
- torch-geometric `2.7.0`
- networkx `3.4.2`
- scapy `2.7.0`

`environment.yml` is provided as a convenience environment definition. `requirements.txt` is the validated Python dependency source of truth used by `scripts/check_env.py --strict`.

## Public Data Bootstrap

`OpenFedBot` does not vendor the graph `.pt` assets directly. Instead, reviewers build them locally from the public `Ca-Bench` captures using the frozen builder snapshot in this repository.

If your checkout already contains:

- `assets/public_cabench_v1/graphs/cabench_scenario_e_three_tier_high2_public_graph.pt`
- `assets/public_cabench_v1/graphs/cabench_scenario_h_mimic_heavy_overlap_public_graph.pt`

you can skip this section.

Otherwise, obtain the public `Ca-Bench` data first:

- repository: [`1251408860-oss/Ca-Bench`](https://github.com/1251408860-oss/Ca-Bench)
- mirrored packet-capture release: [`data-v1`](https://github.com/1251408860-oss/Ca-Bench/releases/tag/data-v1)

The simplest path is a normal checkout or ZIP download of `Ca-Bench`, which already includes:

```bash
mininet_testbed/real_collection/scenario_e_three_tier_high2/full_arena_v2.pcap
mininet_testbed/real_collection/scenario_h_mimic_heavy_overlap/full_arena_v2.pcap
```

From the `OpenFedBot` repository root:

```bash
make PYTHON=/path/to/python prepare-public-assets CABENCH_ROOT=/path/to/Ca-Bench
```

This produces the reviewer-local runtime bundle under `assets/public_cabench_v1/` and writes an `asset_manifest.json` with source hashes and graph statistics.

## Quick Installation

### Option A: create a fresh conda environment

```bash
cd ~/workspace/OpenFedBot
conda env create -f environment.yml
conda activate openfedbot
python scripts/check_env.py --strict
```

### Option B: install into an existing Python 3.10 environment

```bash
cd ~/workspace/OpenFedBot
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
python scripts/check_env.py --strict
```

Notes:

- if a fresh `conda env create` is blocked by transient package-download failures, use Option B in an existing Python `3.10` environment and verify with `scripts/check_env.py --strict`
- if you need GPU acceleration, install the matching official PyTorch wheel first, then run `python -m pip install -e . --no-deps`

## Quick Reviewer Reproduction

After activating a Python `3.10` environment:

```bash
make help
make PYTHON=/path/to/python check-env
make PYTHON=/path/to/python prepare-public-assets CABENCH_ROOT=/path/to/Ca-Bench
make PYTHON=/path/to/python validate-smoke
make PYTHON=/path/to/python smoke
make PYTHON=/path/to/python validate-mainline
make PYTHON=/path/to/python mainline
```

Important runtime behavior:

- the `Makefile` overrides the legacy config roots at runtime, so fresh-clone runs read graphs from `assets/public_cabench_v1/`
- all new outputs land under the repository-local `results/` directory instead of a workspace-external path
- the legacy `hitrust_root` fields remain in the JSON configs for provenance, but they are no longer the default reviewer path

Expected generated directories:

- `results/open_world_mimic_reinforced_smoke_<timestamp>/`
- `results/open_world_full_suite_multiproto_coverageswitch_clean_seed10_<timestamp>/`

Result interpretation:

- Core paper-facing method and triage tables are expected to match exactly when the workflow is followed.
- Runtime and deployment timing summaries are hardware/runtime-stack sensitive and may vary across machines.
- These timing variations do not change the paper's method-level conclusions.

## Digest, Bundle, And Figure Rebuild

From a freshly generated run:

```bash
make PYTHON=/path/to/python digest RUN_DIR=results/open_world_full_suite_multiproto_coverageswitch_clean_seed10_<timestamp>
make PYTHON=/path/to/python bundle DIGEST_DIR=results/reinforced_digest_<timestamp>
```

For the paper figures, generate the two coverage ablations first:

```bash
make PYTHON=/path/to/python cov10
make PYTHON=/path/to/python cov14
make PYTHON=/path/to/python digest RUN_DIR=results/open_world_full_suite_multiproto_coverageswitch_clean_seed10_cov10_<timestamp>
make PYTHON=/path/to/python digest RUN_DIR=results/open_world_full_suite_multiproto_coverageswitch_clean_seed10_cov14_<timestamp>
MAIN_DIGEST=results/reinforced_digest_<mainline_digest_timestamp>
COV10_DIGEST=results/reinforced_digest_<cov10_digest_timestamp>
COV14_DIGEST=results/reinforced_digest_<cov14_digest_timestamp>
make PYTHON=/path/to/python figures \
  DIGEST_DIR=$MAIN_DIGEST \
  COV10_DIGEST_DIR=$COV10_DIGEST \
  COV14_DIGEST_DIR=$COV14_DIGEST
```

If you only want to inspect the frozen paper-facing artifacts without rerunning experiments, use the tracked bundle under `paper_artifacts/`.

## Graph Contract

The preferred runtime contract is a local graph bundle with explicit graph and manifest paths:

```json
{
  "graph_root": "/path/to/public_cabench_assets",
  "scenario_graphs": {
    "scenario_e": {
      "graph_path": "graphs/cabench_scenario_e_three_tier_high2_public_graph.pt",
      "manifest_path": "meta/cabench_scenario_e_three_tier_high2_public_manifest.json"
    }
  }
}
```

The schema is documented in [`docs/graph_schema_contract_v1.md`](./docs/graph_schema_contract_v1.md).

## Additional Notes

- [`REVIEWER_GUIDE.md`](./REVIEWER_GUIDE.md) is the shortest repository overview
- [`repro/README.md`](./repro/README.md) contains the maintained reproduction sequence
- [`assets/README.md`](./assets/README.md) explains the generated public graph layout
- [`results/README.md`](./results/README.md) records how the local results tree was pruned and archived
