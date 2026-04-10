# Reproduction Guide

This directory documents the maintained reproduction path for the reviewer-facing repository.

## Fast Validation Path

After activating a Python 3.10 environment:

```bash
make help
make PYTHON=/home/user/miniconda3/envs/DL/bin/python check-env
make PYTHON=/home/user/miniconda3/envs/DL/bin/python validate-smoke
make PYTHON=/home/user/miniconda3/envs/DL/bin/python smoke
```

## Canonical Digest Rebuild

Rebuild the canonical digest from the frozen clean run:

```bash
make PYTHON=/home/user/miniconda3/envs/DL/bin/python digest-canonical
```

Equivalent direct command:

```bash
python scripts/build_reinforced_digest.py \
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

## Submission Bundle Rebuild

```bash
make PYTHON=/home/user/miniconda3/envs/DL/bin/python bundle
```

## Figure Rebuild

```bash
make PYTHON=/home/user/miniconda3/envs/DL/bin/python figures
```

## Scope Notes

- The tracked `paper_artifacts/` package is the Git-friendly subset intended for direct inspection.
- The raw `results/` tree is a local workspace artifact and is not fully tracked in GitHub.
- Legacy docs and superseded local result directories were archived to keep the current repository focused on the active paper mainline.
