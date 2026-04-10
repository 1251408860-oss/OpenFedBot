# Repro And Submission Playbook

Date: 2026-04-07

This playbook defines the smallest stable path from current code to a WASA-ready submission artifact bundle.

## Authoritative Sources

Use only these as the paper source of truth:

1. run dir:
   `/home/user/workspace/OpenFedBot/results/open_world_full_suite_reviewselector_seed10_20260407T060213Z`
2. digest dir:
   `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z`
3. paper manifest:
   `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/paper_authoritative_manifest.json`
4. run manifest:
   `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/manifest.json`

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
  --config configs/open_world_full_suite_reviewselector_seed10.json
```

Current validation status on 2026-04-07:

1. `scenario_e` passed with `5976` nodes, `8142` edges, and `81` source IPs
2. `scenario_h` passed with `6985` nodes, `9755` edges, and `90` source IPs
3. both graphs emitted the same warning:
   `graph_schema_version is missing; treating graph as a legacy-compatible bundle`

This warning is acceptable for the current submission because the loader validates the required fields successfully. Do not misreport these graphs as native v1 exports.

### 2. Digest Rebuild

Rebuild the digest from the authoritative run and compare outputs:

```bash
python3 scripts/build_reinforced_digest.py \
  --run-dir results/open_world_full_suite_reviewselector_seed10_20260407T060213Z \
  --reference-method cpd_consensus_plus \
  --paper-main-method cpd_consensus_plus \
  --paper-baselines ova_gate msp energy cpd_consensus \
  --paper-main-policy triage_consensus_plus_prototype_or_ova_selective \
  --paper-appendix-policies triage_consensus_plus_prototype_nonbenign triage_consensus_plus_ova_selective \
  --comparators cpd_consensus ova_gate msp energy \
  --bank-selection adaptive \
  --bank-selection-metric cpd_val_coverage \
  --bank-selection-tie-break-metric cpd_val_risk
```

After rebuild, confirm:

1. `manifest.json` records `bank_selection_mode = adaptive`
2. `paper_authoritative_manifest.json` includes `selected_bank_assignments.csv`
3. adaptive paired summaries are present in `authoritative_outputs`

### 3. Main Paper Numbers

Check these before final submission:

1. `paper_main_method_summary.csv`
2. `paper_main_triage_summary.csv`
3. `paper_review_load_summary.csv`
4. `paper_runtime_summary.csv`
5. `adaptive_bank_method_summary.csv`
6. `adaptive_bank_triage_summary.csv`
7. `selected_bank_assignments.csv`

The paper should quote the rounded values from these files only.

## Submission Bundle Build

Build a clean bundle from the authoritative manifest:

```bash
python3 scripts/build_submission_bundle.py \
  --authoritative-manifest results/reinforced_digest_20260407T074024Z/paper_authoritative_manifest.json \
  --paper-draft docs/wasa_paper_draft_20260407.md \
  --playbook docs/repro_submission_playbook_20260407.md \
  --submission-packet docs/wasa_submission_packet_20260407.md \
  --experiment-note docs/reviewselector_fullsuite_experiment_note_20260407.md
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

The bundle should now also include:

1. the adaptive bank note
2. `selected_bank_assignments.csv`
3. adaptive paired summaries
4. fixed-`large` comparison tables

## Mandatory Paper Statements

These points should appear explicitly in the paper:

1. `cpd_consensus_plus` is the automatic gate
2. `triage_consensus_plus_prototype_or_ova_selective` is the deployment policy
3. adaptive bank selection is the paper mainline calibration policy
4. automatic coverage is intentionally conservative
5. hardest `h_to_e_*` cross-scenario protocols remain a limitation
6. the main empirical win is safer unknown routing plus lower benign review load

## Final Reviewer-Facing Checklist

1. Every headline claim has a matching CSV or PNG in the authoritative digest.
2. Every quoted number is rounded from the authoritative digest, not from old notes.
3. The limitations paragraph includes the hardest cross protocols explicitly.
4. The review-load section compares the new policy against `triage_consensus_plus_ova`.
5. The calibration section explains the adaptive selection rule.
6. The reproducibility section names the graph schema contract and the frozen Ca-Bench snapshot.
7. The paper never claims `80%+` acceptance certainty.

## What Not To Do

1. do not switch the mainline back to fixed `large`
2. do not switch the mainline back to `triage_consensus_plus_ova`
3. do not present `cpd_adapt` as the main method
4. do not promote `hybrid pseudo` beyond appendix ablations
5. do not merge old digest numbers from `042017Z`
6. do not hide the hardest-protocol limitation
