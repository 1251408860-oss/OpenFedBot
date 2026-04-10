# Reproduction Guide

This guide documents the maintained reviewer path for reproducing `OpenFedBot` from a fresh clone.

## Scope

The repository tracks a paper-facing artifact snapshot under `paper_artifacts/`, while runtime graph assets and new experiment outputs are generated locally.

## A. Environment Setup

From the repository root:

```bash
conda env create -f environment.yml
conda activate openfedbot
python scripts/check_env.py --strict
```

If network instability prevents `conda env create`, install dependencies in an existing Python `3.10` environment with:

```bash
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
python scripts/check_env.py --strict
```

## B. Public Data Bootstrap

Download or clone public `Ca-Bench` and point `CABENCH_ROOT` at that checkout:

```bash
make PYTHON=/path/to/python prepare-public-assets CABENCH_ROOT=/path/to/Ca-Bench
```

This step builds and validates reviewer-local graph assets at:

- `assets/public_cabench_v1/graphs/`
- `assets/public_cabench_v1/meta/`
- `assets/public_cabench_v1/asset_manifest.json`

## C. Smoke Reproduction

```bash
make PYTHON=/path/to/python validate-smoke
make PYTHON=/path/to/python smoke
```

Expected output:

- `results/open_world_mimic_reinforced_smoke_<timestamp>/`

## D. Mainline Reproduction

```bash
make PYTHON=/path/to/python validate-mainline
make PYTHON=/path/to/python mainline
```

Expected output:

- `results/open_world_full_suite_multiproto_coverageswitch_clean_seed10_<timestamp>/`

## E. Digest And Bundle Rebuild

Use the generated mainline run directory:

```bash
make PYTHON=/path/to/python digest RUN_DIR=results/open_world_full_suite_multiproto_coverageswitch_clean_seed10_<timestamp>
make PYTHON=/path/to/python bundle DIGEST_DIR=results/reinforced_digest_<timestamp>
```

Expected output:

- `results/reinforced_digest_<timestamp>/`
- `results/submission_bundle_<timestamp>/`

## F. Figure Rebuild

Generate cov10 and cov14 runs, digest them, then build figures:

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

Expected output:

- `results/wasa_main_figures_<timestamp>/`

## G. Reproduction Interpretation

The maintained target is:

- core paper tables and the operating-frontier figure should match the reference values
- runtime and deployment timing summaries may vary across hardware and runtime stacks
- manifest and bundle metadata files naturally differ by timestamp and path
