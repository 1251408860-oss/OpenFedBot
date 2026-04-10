# OpenFedBot

This repository contains the reviewer-facing implementation snapshot and paper artifact package for `OpenFedBot`, a deployment-oriented open-world federated bot triage system on graph data.

`OpenFedBot` trains a GraphSAGE + FedAvg backbone, calibrates open-world decision rules, evaluates deployment-time triage policies, and produces paper-facing digests, figures, and submission bundles.

## Repository Navigation And Artifact Mapping

| Scope | Directory / File | Purpose |
| --- | --- | --- |
| Core implementation | `openfedbot/` | training, calibration, metrics, schema loading, reporting |
| Experiment entrypoints | `scripts/` | run experiments, validate graph bundles, rebuild digests, build bundles, build figures |
| Runnable configs | `configs/` | current configs plus local-graph example configs |
| Paper-facing tracked artifacts | `paper_artifacts/` | reviewer-sized bundle mirrored from the active workspace |
| Reproduction guide | `repro/README.md` | quick checks, smoke path, canonical digest rebuild, bundle rebuild |
| Active documentation | `docs/` | graph schema and current paper-facing notes |
| Provenance snapshot | `third_party/cabench_frozen/` | frozen local Ca-Bench snapshot used for provenance control |
| Local generated outputs | `results/` | non-tracked local runs, digests, bundles, and archived workspace artifacts |
| Release checklist | `RELEASE_CHECKLIST.md` | reviewer-facing repository and release sanity checks |

## Reviewer Fast Path

If you only want the paper-facing materials, start here:

1. [`paper_artifacts/README.md`](paper_artifacts/README.md)
2. [`paper_artifacts/submission_bundle_20260409/`](paper_artifacts/submission_bundle_20260409/)
3. [`paper_artifacts/submission_bundle_20260409/tables/`](paper_artifacts/submission_bundle_20260409/tables/)
4. [`paper_artifacts/submission_bundle_20260409/figures/`](paper_artifacts/submission_bundle_20260409/figures/)
5. [`paper_artifacts/submission_bundle_20260409/docs/`](paper_artifacts/submission_bundle_20260409/docs/)

The active paper-facing chain behind this repository is:

1. canonical clean run in the original workspace:
   `results/open_world_full_suite_multiproto_coverageswitch_clean_seed10_20260408T023210Z`
2. canonical clean digest:
   `results/digest_cov12/reinforced_digest_20260408T040419Z`
3. tracked paper artifact bundle:
   `paper_artifacts/submission_bundle_20260409/`

## Global Environment Overview

This repository was validated against the existing `Ubuntu5` / `DL` environment on `2026-04-10`:

- Python `3.10.19`
- numpy `2.2.6`
- scipy `1.15.3`
- matplotlib `3.10.8`
- scikit-learn `1.7.2`
- torch `2.10.0` (`2.10.0+cu128` in the original local environment)
- torch-geometric `2.7.0`

The repository does not currently include a dedicated unit-test suite. The maintained validation path is:

1. `scripts/check_env.py --strict`
2. `scripts/validate_graph_schema.py --config <config>`
3. a smoke experiment run
4. regeneration of digest / bundle / figures from the frozen canonical run

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

- `requirements.txt` tracks the versions validated in the local workspace.
- If you need GPU acceleration, install the matching official PyTorch wheel first, then run `python -m pip install -e . --no-deps`.

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

The schema is documented in [`docs/graph_schema_contract_v1.md`](docs/graph_schema_contract_v1.md).

For local-graph examples, start with:

- `configs/open_world_mimic_reinforced_smoke_local_graphs.example.json`
- `configs/open_world_full_suite_multiproto_coverageswitch_clean_seed10_local_graphs.example.json`

Legacy `hitrust_root` configs are still included for compatibility with the original workspace layout.

## Quick Commands

Use the `Makefile` as the single entrypoint after activating your environment:

```bash
make help
make check-env
make validate-smoke
make smoke
make digest-canonical
make bundle
```

To pin the interpreter explicitly:

```bash
make PYTHON=/home/user/miniconda3/envs/DL/bin/python check-env
```

## Additional Notes

- [`repro/README.md`](repro/README.md) contains the practical reproduction path.
- [`REVIEWER_GUIDE.md`](REVIEWER_GUIDE.md) is a short reviewer-oriented summary.
- [`results/README.md`](results/README.md) explains how the local workspace results tree was pruned and archived.
