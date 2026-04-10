# OpenFedBot Reviewer Release

Date: 2026-04-10

This release is a reviewer-facing source snapshot of `OpenFedBot`.

## Included

- source code for training, calibration, schema validation, reporting, and artifact generation
- configs used in the current workspace, with reviewer defaults now pointing to repo-local graph and results roots
- active paper-facing documentation
- a tracked paper artifact bundle in `paper_artifacts/submission_bundle_20260409/`
- a zip asset for easy download: `OpenFedBot-reviewer-20260409.zip`

## Reviewer Entry Points

- `README.md`
- `REVIEWER_GUIDE.md`
- `paper_artifacts/submission_bundle_20260409/tables/`
- `paper_artifacts/submission_bundle_20260409/figures/`
- `paper_artifacts/submission_bundle_20260409/docs/`

## Validation Performed

The repository was checked in the local `Ubuntu5` / `DL` environment with:

1. `scripts/check_env.py --strict`
2. `make prepare-public-assets CABENCH_ROOT=<local-Ca-Bench-checkout>`
3. schema validation of maintained smoke and mainline configs
4. fresh smoke and mainline runs using repo-local assets and outputs
5. digest rebuild from a fresh mainline run
6. submission bundle rebuild from the fresh digest

## Scope Notes

- The full raw experiment runs are not tracked in GitHub because they are large generated artifacts.
- The tracked reviewer bundle is intentionally small and paper-facing.
- Public graph assets are built locally from `Ca-Bench` (`assets/public_cabench_v1/`) and are intentionally ignored by Git.
- Runtime and deployment timing tables are expected to vary across hardware/runtime stacks; this does not affect method-level paper conclusions.
- Legacy drafts, notes, and older result directories were archived locally so the repository surface stays focused on the current mainline.
