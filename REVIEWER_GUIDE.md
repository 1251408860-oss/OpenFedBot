# Reviewer Guide

This repository is organized as a reviewer-facing source snapshot plus a tracked paper artifact package.

## Start Here

1. [`README.md`](README.md)
2. [`paper_artifacts/README.md`](paper_artifacts/README.md)
3. [`paper_artifacts/submission_bundle_20260409/tables/`](paper_artifacts/submission_bundle_20260409/tables/)
4. [`paper_artifacts/submission_bundle_20260409/figures/`](paper_artifacts/submission_bundle_20260409/figures/)
5. [`paper_artifacts/submission_bundle_20260409/docs/`](paper_artifacts/submission_bundle_20260409/docs/)

## Repository Scope

Included:

- source code, configs, schema docs
- a tracked paper artifact bundle
- a practical reproduction path

Not included:

- the full raw experiment outputs from the original `results/` workspace
- the external graph assets referenced by the legacy `hitrust_root` configs

## Reproduction Entry Point

See [`repro/README.md`](repro/README.md) for the maintained validation path:

- environment check
- graph schema validation
- smoke run
- canonical digest rebuild
- bundle rebuild
- figure rebuild
