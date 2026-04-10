# Repro And Submission Playbook

Date: 2026-04-09

This playbook defines the smallest stable path from current code to a WASA-ready submission artifact bundle aligned with the `2026-04-08` canonical mainline.

## Authoritative Sources

Use only these as the paper source of truth:

1. clean run dir:
   `/home/user/workspace/OpenFedBot/results/open_world_full_suite_multiproto_coverageswitch_clean_seed10_20260408T023210Z`
2. clean digest dir:
   `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z`
3. stress digest dir:
   `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260408T034757Z`
4. paper manifest:
   `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/paper_authoritative_manifest.json`
5. run manifest:
   `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/manifest.json`

If a table, figure, or number does not trace back to these files, do not use it in the paper.

## Environment

Run inside `Ubuntu5`:

```bash
cd ~/workspace/OpenFedBot
source ~/miniconda3/etc/profile.d/conda.sh
conda activate DL
```

## Pre-Submission Integrity Checks

### 1. Graph Contract

Validate the graph inputs:

```bash
python3 scripts/validate_graph_schema.py \
  --config configs/open_world_full_suite_multiproto_coverageswitch_clean_seed10.json
```

Do not silently switch back to the older reviewselector config.

### 2. Digest Rebuild

Rebuild the clean canonical digest from the authoritative run and compare outputs:

```bash
python3 scripts/build_reinforced_digest.py \
  --run-dir results/open_world_full_suite_multiproto_coverageswitch_clean_seed10_20260408T023210Z \
  --reference-method cpd_shift_multiproto_consensus_plus \
  --paper-main-method cpd_shift_multiproto_consensus_plus \
  --paper-baselines cpd_shift_consensus_plus cpd_shift_multiproto_coverage_switch_plus ova_gate msp energy \
  --paper-main-policy triage_shift_multiproto_coverage_switch_plus_ova_nonbenign \
  --paper-appendix-policies triage_shift_multiproto_consensus_plus_ova_nonbenign triage_shift_multiproto_consensus_gate_plus_ova_nonbenign \
  --comparators cpd_shift_consensus_plus cpd_shift_multiproto_coverage_switch_plus cpd_shift_multiproto_consensus_gate_plus \
  --bank-selection adaptive \
  --bank-selection-metric cpd_val_coverage \
  --bank-selection-tie-break-metric cpd_val_risk
```

After rebuild, confirm:

1. `manifest.json` records `reference_method = cpd_shift_multiproto_consensus_plus`
2. `paper_authoritative_manifest.json` records `paper_main_method = cpd_shift_multiproto_consensus_plus`
3. `paper_authoritative_manifest.json` records `paper_main_policy = triage_shift_multiproto_coverage_switch_plus_ova_nonbenign`
4. adaptive paired summaries are present for the three intended comparators
5. `selected_bank_assignments.csv` is present

### 3. Main Paper Numbers

Check these before final submission:

1. `paper_main_method_summary.csv`
2. `paper_main_triage_summary.csv`
3. `paper_review_load_summary.csv`
4. `paper_deployment_summary.csv`
5. `paper_deployment_protocol_summary.csv`
6. `adaptive_paired_cpd_shift_multiproto_consensus_plus_vs_cpd_shift_consensus_plus_summary.csv`
7. `adaptive_paired_cpd_shift_multiproto_consensus_plus_vs_cpd_shift_multiproto_coverage_switch_plus_summary.csv`
8. `selected_bank_assignments.csv`

Quote rounded values from these files only.

### 4. Threshold And Stress Separation

Before submission, confirm the writing obeys this split:

1. `digest_cov12` is the canonical paper source
2. `digest_cov10` and `digest_cov14` are threshold-selection support only
3. `reinforced_digest_20260408T034757Z` is stress robustness support only
4. no deployment-time number in the main text is taken from the stress digest

## Submission Bundle Build

Build a clean bundle from the canonical manifest:

```bash
python3 scripts/build_submission_bundle.py \
  --authoritative-manifest results/digest_cov12/reinforced_digest_20260408T040419Z/paper_authoritative_manifest.json \
  --paper-draft docs/wasa_paper_draft_20260409.md \
  --playbook docs/repro_submission_playbook_20260409.md \
  --submission-packet docs/wasa_submission_packet_20260409.md \
  --experiment-note docs/wasa_submission_convergence_20260408.md
```

The script creates `results/submission_bundle_<timestamp>` and copies the paper-facing artifacts into a stable tree.

## Bundle Contents

The bundle should contain:

1. `tables/`
2. `figures/`
3. `docs/`
4. `manifests/`
5. `scripts/`
6. `configs/`
7. `bundle_manifest.json`

The bundle must now include:

1. the clean canonical manifest
2. the `20260409` paper draft, packet, and playbook
3. `wasa_submission_convergence_20260408.md`
4. `selected_bank_assignments.csv`
5. the new multiproto coverageswitch config

The bundle must not include:

1. `wasa_paper_draft_20260407.md`
2. `wasa_submission_packet_20260407.md`
3. `repro_submission_playbook_20260407.md`
4. `configs/open_world_full_suite_reviewselector_seed10.json`

## Mandatory Paper Statements

These points should appear explicitly in the paper:

1. `cpd_shift_multiproto_consensus_plus` is the safe auto backbone
2. `triage_shift_multiproto_coverage_switch_plus_ova_nonbenign` is the deployment operating policy
3. adaptive bank selection is the calibration policy used to build the canonical digest
4. `actionable_coverage` is the deployment-facing metric
5. hardest cross protocols remain a limitation
6. the main empirical win is safer deployment, not higher automation

## Final Reviewer-Facing Checklist

1. Every headline claim has a matching CSV or PNG in the canonical digest.
2. Every quoted number traces back to `digest_cov12/reinforced_digest_20260408T040419Z`.
3. The limitations paragraph includes the hardest cross protocols explicitly.
4. The deployment section distinguishes automatic coverage from actionable coverage.
5. The method section distinguishes the safe backbone from the coverage-switch operating policy.
6. The reproducibility section names the graph schema contract and the frozen Ca-Bench snapshot.
7. The bundle manifest includes only new-mainline docs and config.

## What Not To Do

1. do not switch the mainline back to the `20260407` reviewselector digest
2. do not present `cpd_shift_multiproto_coverage_switch_plus` as the paper's automatic backbone
3. do not quote the stress digest for deployment cost
4. do not mix `cov10` or `cov14` into the main paper numbers
5. do not hide the hardest-protocol limitation
6. do not use the old reviewselector config in the final bundle
