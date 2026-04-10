# WASA Submission Packet

Date: 2026-04-07

## Stable Paper Positioning

Use the paper as a deployment-oriented systems paper, not as a claim of a universally stronger single-stage classifier.

The stable narrative is:

1. `cpd_consensus_plus` with adaptive bank selection is the primary automatic gate.
2. `triage_consensus_plus_prototype_or_ova_selective` with the same adaptive bank policy is the primary deployment pipeline.
3. The paper's strongest evidence is safer unknown routing, fewer benign false alerts, better cross-scenario operating points than the fixed `large` calibration mainline, and materially bounded review burden relative to the older `triage_consensus_plus_ova` path.

## Authoritative Artifact Bundle

Use this digest as the single source of truth for the paper:

- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z`

Writing and submission support docs:

- `/home/user/workspace/OpenFedBot/docs/adaptive_bank_fullsuite_note_20260407.md`
- `/home/user/workspace/OpenFedBot/docs/wasa_paper_draft_20260407.md`
- `/home/user/workspace/OpenFedBot/docs/repro_submission_playbook_20260407.md`

The authoritative file manifest is:

- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/paper_authoritative_manifest.json`

Primary paper-facing tables:

- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/paper_main_method_summary.csv`
- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/paper_main_triage_summary.csv`
- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/paper_review_load_summary.csv`
- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/paper_runtime_summary.csv`

Primary paper-facing support artifacts:

- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/paper_operating_frontier.csv`
- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/paper_operating_frontier.png`
- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/hardest_cpd_consensus_protocols.csv`
- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/hardest_triage_consensus_ova_protocols.csv`
- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/hardest_protocol_method_comparison.csv`
- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/selected_bank_assignments.csv`
- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/adaptive_paired_cpd_consensus_plus_vs_ova_gate_summary.csv`
- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/adaptive_paired_cpd_consensus_plus_vs_msp_summary.csv`
- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/adaptive_paired_cpd_consensus_plus_vs_energy_summary.csv`
- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/adaptive_paired_cpd_consensus_plus_vs_cpd_consensus_summary.csv`

Note:

1. `hardest_triage_consensus_ova_protocols.csv` is a legacy digest filename.
2. The current paper mainline is still `triage_consensus_plus_prototype_or_ova_selective`.
3. Keep the paper naming aligned to the current main policy, but explicitly state that the calibration policy is now adaptive.

## Claims To Keep

Keep these as the primary claims:

1. `cpd_consensus_plus` sharply reduces unknown misrouting against `OVA`, `MSP`, and `Energy`.
2. `cpd_consensus_plus` also reduces benign false alerts with paired statistical support.
3. adaptive bank selection improves the cross-scenario operating point over the fixed `large` calibration bank and materially improves the hardest `h_to_e_*` automatic transfers.
4. `triage_consensus_plus_prototype_or_ova_selective` lifts cross-scenario actionable coverage to `0.6781` while preserving `0.9792` safe unknown handling.
5. the new selective review policy keeps cross `review_benign_rate` near `0.1918`, far below `triage_consensus_plus_ova` under the same adaptive digest (`0.4323`).
6. runtime and communication overhead remain small enough to support an edge deployment story.

## Claims To Avoid

Do not write these as headline claims:

1. single-stage automatic coverage is already high
2. adaptive bank selection solves the hardest cross-scenario protocols
3. `cpd_consensus_plus` is strictly better than `cpd_consensus` on every metric
4. selective risk is comprehensively significant against every baseline
5. review is free
6. `hybrid pseudo` is the new mainline

## Main Tables

Use this table structure:

1. Main Table 1: `cpd_consensus_plus` vs `OVA`, `MSP`, `Energy`, with `cpd_consensus` retained as a comparison row.
   Source: `paper_main_method_summary.csv` + adaptive paired summaries.
2. Main Table 2: `triage_consensus_plus_prototype_or_ova_selective`.
   Include `auto_coverage`, `actionable_coverage`, `final_defer_rate`, `review_benign_rate`, `safe_unknown_handling_rate`, and runtime/communication.
3. Main Table 3: cross vs same breakdown, explicitly marked as adaptive-bank results.

Appendix:

1. `cpd_strict`, `cpd_adapt`, `cpd_adapt_consensus`
2. fixed `large` vs adaptive calibration bank comparison
3. hardest protocol comparison
4. alternative review policies:
   `triage_consensus_plus_prototype_nonbenign`
   `triage_consensus_plus_ova_selective`
   `triage_consensus_plus_ova`
5. `hybrid pseudo` targeted ablations

## Figures

Use these figures first:

1. System overview: conservative auto gate followed by review analyzer.
2. Operating frontier:
   `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/paper_operating_frontier.png`
3. Hardest protocol case study:
   build from `hardest_cpd_consensus_protocols.csv` and `hardest_protocol_method_comparison.csv`
4. adaptive bank selection case study:
   summarize `selected_bank_assignments.csv`

## Reviewer-Facing Weak Points

These are the most likely reviewer attack points and should be answered explicitly:

1. Why not just relax the automatic threshold?
   Answer with the operating frontier and the two-stage deployment argument.
2. Why not keep a fixed `large` bank?
   Answer with `selected_bank_assignments.csv`, `clean_large_method_summary.csv`, and the hardest-cross improvement numbers.
3. Why is review load still non-zero?
   Answer with `paper_review_load_summary.csv` and `adaptive_bank_triage_summary.csv`. Emphasize that the mainline is far lower than `triage_consensus_plus_ova`, but do not claim zero human cost.
4. What still fails?
   Answer with the hardest-protocol files and a limitations paragraph.

## Submission Execution

Before final submission:

1. rebuild or verify the authoritative digest
2. write the paper from `wasa_paper_draft_20260407.md`
3. build a clean bundle with `scripts/build_submission_bundle.py`
4. quote only numbers that trace back to the authoritative digest

## Regeneration Command

Rebuild the authoritative digest with:

```bash
cd ~/workspace/OpenFedBot
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
