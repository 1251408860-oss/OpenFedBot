# OpenFedBot Reviewer Release

Date: 2026-04-10

This release is a reviewer-facing source snapshot of `OpenFedBot`.

## Included

- source code for training, calibration, schema validation, reporting, and artifact generation
- configs used in the current workspace, including local-graph example configs
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
2. schema validation of the maintained smoke config
3. a fresh smoke run
4. regeneration of the canonical digest from the frozen clean run
5. regeneration of the submission bundle
6. regeneration of the paper-facing figures

## Scope Notes

- The full raw experiment runs are not tracked in GitHub because they are large generated artifacts.
- The tracked reviewer bundle is intentionally small and paper-facing.
- Legacy drafts, notes, and older result directories were archived locally so the repository surface stays focused on the current mainline.
