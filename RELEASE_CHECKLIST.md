# Release Checklist

Use this checklist before publishing a reviewer-facing repository snapshot or GitHub release.

## Repository Surface

- top-level README points reviewers to `paper_artifacts/` and `repro/`
- `docs/` top level contains only the active paper-facing documents
- legacy docs remain under `docs/_archive_legacy_20260409/`
- `results/` top level remains pruned and indexed by `results/README.md`

## Paper Artifact Package

- `paper_artifacts/submission_bundle_20260409/` exists
- `paper_artifacts/submission_bundle_20260409/tables/` contains the paper-facing CSVs
- `paper_artifacts/submission_bundle_20260409/figures/paper_operating_frontier.png` exists
- `paper_artifacts/submission_bundle_20260409/manifests/paper_authoritative_manifest.json` exists

## Reproduction Checks

- `scripts/check_env.py --strict` passes in the validated environment
- maintained smoke config validates
- smoke run completes
- canonical digest rebuild completes
- submission bundle rebuild completes
- paper-facing figure rebuild completes

## Release Packaging

- GitHub `main` points at the latest reviewer-facing commit
- reviewer release notes match the current repository layout
- the release asset `OpenFedBot-reviewer-20260409.zip` is attached
