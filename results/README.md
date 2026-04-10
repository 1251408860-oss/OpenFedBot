# Results Layout

This directory was pruned on `2026-04-09` to keep only the current paper-facing artifacts and one recent smoke verification run at the top level.

As of `2026-04-10`, reviewer commands (`make smoke`, `make mainline`, `make digest`, `make bundle`) default to writing all new outputs into this repository-local `results/` tree.

## Active Top-Level Artifacts

- `digest_cov10/`: threshold-sweep support digest for coverage `0.10`
- `digest_cov12/`: current canonical clean digest and paper source of truth
- `digest_cov14/`: threshold-sweep support digest for coverage `0.14`
- `open_world_full_suite_multiproto_coverageswitch_clean_seed10_20260408T023210Z/`: canonical clean run backing `digest_cov12`
- `open_world_full_suite_multiproto_coverageswitch_clean_seed10_cov10_20260408T034944Z/`: clean run used for `cov10`
- `open_world_full_suite_multiproto_coverageswitch_clean_seed10_cov14_20260408T034944Z/`: clean run used for `cov14`
- `reinforced_digest_20260408T034757Z/`: stress robustness digest
- `submission_bundle_20260409T012614Z/`: latest stable submission bundle
- `wasa_main_figures_20260409T023651Z/`: latest generated paper-facing figures
- `open_world_mimic_reinforced_smoke_20260409T091616Z/`: recent smoke run used to re-check repository reproducibility

## Archived Legacy Artifacts

All older non-mainline run directories, outdated digests, older bundles, and superseded figure exports were moved to:

- `_archive_legacy_20260409/`

The archive currently contains `117` top-level directories plus one legacy launch log. Nothing was permanently deleted during this cleanup step.

## Canonical Chain

The current paper-facing chain is:

1. `open_world_full_suite_multiproto_coverageswitch_clean_seed10_20260408T023210Z/`
2. `digest_cov12/reinforced_digest_20260408T040419Z/`
3. `submission_bundle_20260409T012614Z/`

If you need paper numbers, quote from the `digest_cov12` canonical digest rather than from raw run directories.
