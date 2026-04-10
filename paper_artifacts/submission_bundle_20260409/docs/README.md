# OpenFedBot

Deployment-safe open-world federated bot triage experiments built inside `Ubuntu5`.

This workspace studies a two-layer deployment stack for federated graph-based bot detection:

- leave-one-family-out protocol
- same-scenario and cross-scenario evaluation
- GraphSAGE + FedAvg training
- temperature scaling and adaptive calibration-bank selection
- class-wise single-prototype and multi-prototype gating
- target-time pseudo adaptation with prototype-bank alignment
- safe auto backbone evaluation
- deployment-time triage and review-load accounting
- deployment cost reporting
- missing-neighbor stress tests via edge dropout / boundary neighbor removal
- supplemental `OVA`, `MSP`, and `Energy` open-world baselines
- selective-risk, unknown-routing, and operating-frontier reporting

`Ca-Bench` is treated as one valid external graph source, not as an implicit upstream toolchain dependency. The preferred runtime contract is a local graph bundle that satisfies the OpenFedBot graph schema documented in [docs/graph_schema_contract_v1.md](./docs/graph_schema_contract_v1.md).

## Layout

- `configs/`: runnable experiment configs
- `openfedbot/`: protocol, training, calibration, metrics, and reporting code
- `scripts/`: experiment entry points
- `results/`: generated runs, tables, figures, and summaries
- `third_party/cabench_frozen/`: frozen local snapshot of the Ca-Bench builder used for provenance control

## Data Contract

The preferred config format is based on `graph_root` plus explicit graph and manifest paths:

```json
{
  "graph_root": "/path/to/public_cabench_assets",
  "scenario_graphs": {
    "scenario_e": {
      "graph_path": "graphs/cabench_scenario_e_three_tier_high2_public_graph.pt",
      "manifest_path": "meta/cabench_scenario_e_three_tier_high2_public_manifest.json"
    }
  }
}
```

Legacy `hitrust_root`-style configs are still supported for compatibility, but they are no longer the preferred interface.

Validate a graph bundle before running experiments:

```bash
cd ~/workspace/OpenFedBot
python scripts/validate_graph_schema.py --config configs/open_world_full_suite_multiproto_coverageswitch_clean_seed10.json
```

## Default Run

Inside `Ubuntu5`:

```bash
cd ~/workspace/OpenFedBot
source ~/miniconda3/etc/profile.d/conda.sh
conda activate DL
python scripts/run_experiment.py --config configs/open_world_mimic_main.json
```

The default config runs:

- `same_e_mimic`: same-scenario temporal test on `scenario_e`
- `e_to_h_mimic`: `scenario_e -> scenario_h`
- `h_to_e_mimic`: `scenario_h -> scenario_e`

using seeds `11, 42, 111`.

## Reinforced Suite

To run the 10-seed clean canonical suite behind the current paper-facing mainline:

```bash
cd ~/workspace/OpenFedBot
source ~/miniconda3/etc/profile.d/conda.sh
conda activate DL
python scripts/run_experiment.py --config configs/open_world_full_suite_multiproto_coverageswitch_clean_seed10.json
python3 scripts/build_reinforced_digest.py \
  --run-dir results/open_world_full_suite_multiproto_coverageswitch_clean_seed10_<timestamp> \
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

To rebuild the current canonical digest from the frozen clean run:

```bash
cd ~/workspace/OpenFedBot
source ~/miniconda3/etc/profile.d/conda.sh
conda activate DL
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

## Authoritative WASA Package

The current paper-facing mainline is frozen to:

- clean canonical run: `results/open_world_full_suite_multiproto_coverageswitch_clean_seed10_20260408T023210Z`
- clean canonical digest: `results/digest_cov12/reinforced_digest_20260408T040419Z`
- stress robustness digest: `results/reinforced_digest_20260408T034757Z`
- safe auto backbone: `cpd_shift_multiproto_consensus_plus`
- calibration policy: `adaptive bank selection`
- deployment policy: `triage_shift_multiproto_coverage_switch_plus_ova_nonbenign`
- appendix auto comparator: `cpd_shift_multiproto_consensus_gate_plus`
- coverage-switch activation threshold: `shift_hybrid_activation_coverage = 0.12`

The adaptive selector is a local digest-time policy layered on top of the frozen clean run:

1. read `calibration_metrics.csv`
2. choose one bank per `(protocol, seed)`
3. maximize `cpd_val_coverage`
4. tie-break with minimum `cpd_val_risk`

Use the clean canonical digest for:

1. main tables
2. deployment cost and review-load numbers
3. hardest-protocol discussion
4. threshold-sweep justification

Use the stress digest only for robustness and supplement. Do not quote its deployment-time numbers as real deployment cost because the stress run contains multiple perturbations.

The authoritative digest includes:

- `selected_bank_assignments.csv`
- `paper_main_method_summary.csv`
- `paper_main_triage_summary.csv`
- `paper_review_load_summary.csv`
- `paper_deployment_summary.csv`
- `paper_deployment_protocol_summary.csv`
- `deployment_seed_metrics.csv`
- adaptive paired summaries against `cpd_shift_consensus_plus`, `cpd_shift_multiproto_coverage_switch_plus`, and `cpd_shift_multiproto_consensus_gate_plus`

Paper-writing and submission docs:

- `docs/wasa_submission_convergence_20260408.md`
- `docs/wasa_submission_packet_20260409.md`
- `docs/wasa_paper_draft_20260409.md`
- `docs/repro_submission_playbook_20260409.md`

Build a stable submission bundle:

```bash
cd ~/workspace/OpenFedBot
source ~/miniconda3/etc/profile.d/conda.sh
conda activate DL
python3 scripts/build_submission_bundle.py \
  --authoritative-manifest results/digest_cov12/reinforced_digest_20260408T040419Z/paper_authoritative_manifest.json \
  --paper-draft docs/wasa_paper_draft_20260409.md \
  --playbook docs/repro_submission_playbook_20260409.md \
  --submission-packet docs/wasa_submission_packet_20260409.md \
  --experiment-note docs/wasa_submission_convergence_20260408.md
```

## Direct Graph Example

A direct local-graph example config is included at:

```bash
configs/open_world_full_suite_reinforced_seed10_local_graphs.example.json
```

Use it when you want to run `OpenFedBot` from a local graph asset directory without depending on the `HiTrust-FedBot` repository layout.
