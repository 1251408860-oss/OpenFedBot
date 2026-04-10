# Reviewer Guide

This is the shortest practical path for reviewers who want to rerun `OpenFedBot` from a fresh clone.

## 1) Prepare Environment

Use Python `3.10` and install dependencies:

```bash
conda env create -f environment.yml
conda activate openfedbot
python scripts/check_env.py --strict
```

If `conda env create` is blocked by transient package-download failures, install with `requirements.txt` in an existing Python `3.10` environment, then rerun `python scripts/check_env.py --strict`.

## 2) Build Public Graph Assets

`OpenFedBot` expects graph `.pt` assets but does not track them in Git. Build them locally from public `Ca-Bench` captures:

```bash
make PYTHON=/path/to/python prepare-public-assets CABENCH_ROOT=/path/to/Ca-Bench
```

This creates:

- `assets/public_cabench_v1/graphs/cabench_scenario_e_three_tier_high2_public_graph.pt`
- `assets/public_cabench_v1/graphs/cabench_scenario_h_mimic_heavy_overlap_public_graph.pt`
- `assets/public_cabench_v1/meta/*.json`

## 3) Run Reviewer Validation

```bash
make PYTHON=/path/to/python check-env
make PYTHON=/path/to/python validate-smoke
make PYTHON=/path/to/python smoke
```

Optional full mainline:

```bash
make PYTHON=/path/to/python validate-mainline
make PYTHON=/path/to/python mainline
```

## 4) Outputs

Fresh-clone outputs are written under repository-local `results/`:

- `results/open_world_mimic_reinforced_smoke_<timestamp>/`
- `results/open_world_full_suite_multiproto_coverageswitch_clean_seed10_<timestamp>/`

No default command writes to `/home/user/workspace/HiTrust-FedBot/...` or any workspace-external results directory.

## 5) Paper-Facing Artifacts

If you only need the paper-facing snapshot, inspect:

- `paper_artifacts/submission_bundle_20260409/`
