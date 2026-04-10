# WASA Submission Packet

Date: 2026-04-09

## Stable Paper Positioning

Use the paper as a deployment-oriented systems paper for edge and networked AI threat detection, not as a claim of a universally stronger high-automation single-stage classifier.

The stable narrative is:

1. `cpd_shift_multiproto_consensus_plus` is the safe automatic backbone.
2. `triage_shift_multiproto_coverage_switch_plus_ova_nonbenign` is the primary deployment pipeline.
3. adaptive calibration-bank selection is the paper-facing calibration policy.
4. the strongest evidence is `actionable_coverage`, `safe_unknown_handling_rate`, low `review_benign_rate`, and explicit deployment-cost accounting.

## Authoritative Artifact Bundle

Use this clean canonical digest as the single source of truth for the main paper:

- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z`

Use this stress digest only for robustness and supplement:

- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260408T034757Z`

Writing and submission support docs:

- `/home/user/workspace/OpenFedBot/docs/wasa_submission_convergence_20260408.md`
- `/home/user/workspace/OpenFedBot/docs/wasa_paper_draft_20260409.md`
- `/home/user/workspace/OpenFedBot/docs/repro_submission_playbook_20260409.md`
- `/home/user/workspace/OpenFedBot/docs/wasa_submission_packet_20260409.md`

The authoritative file manifest is:

- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/paper_authoritative_manifest.json`

Primary paper-facing tables:

- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/paper_main_method_summary.csv`
- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/paper_main_triage_summary.csv`
- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/paper_review_load_summary.csv`
- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/paper_deployment_summary.csv`
- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/paper_deployment_protocol_summary.csv`

Primary paper-facing support artifacts:

- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/paper_operating_frontier.csv`
- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/paper_operating_frontier.png`
- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/hardest_cpd_consensus_protocols.csv`
- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/hardest_triage_consensus_ova_protocols.csv`
- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/hardest_protocol_method_comparison.csv`
- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/selected_bank_assignments.csv`
- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/adaptive_paired_cpd_shift_multiproto_consensus_plus_vs_cpd_shift_consensus_plus_summary.csv`
- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/adaptive_paired_cpd_shift_multiproto_consensus_plus_vs_cpd_shift_multiproto_coverage_switch_plus_summary.csv`
- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/adaptive_paired_cpd_shift_multiproto_consensus_plus_vs_cpd_shift_multiproto_consensus_gate_plus_summary.csv`

Note:

1. `hardest_triage_consensus_ova_protocols.csv` is still a legacy digest filename.
2. The current main policy is `triage_shift_multiproto_coverage_switch_plus_ova_nonbenign`.
3. The current main automatic method is `cpd_shift_multiproto_consensus_plus`.
4. The clean canonical digest is the only valid source for deployment-cost numbers.

## Claims To Keep

Keep these as the primary claims:

1. `cpd_shift_multiproto_consensus_plus` is a safer automatic backbone than aggressive open-world baselines.
2. The cleanest paired gain over `cpd_shift_consensus_plus` is lower `accepted_benign_fpr`, not universal significance on every metric.
3. `triage_shift_multiproto_coverage_switch_plus_ova_nonbenign` lifts cross `actionable_coverage` to `0.4773` while preserving `safe_unknown_handling_rate = 0.9779`.
4. The deployment operating policy keeps cross `review_benign_rate` near `0.0018`, which is low enough to support a deployment story.
5. Multi-prototype representation improves deployment usability on hardest cross protocols even though those protocols remain unsolved at the automatic stage.
6. Deployment-cost evidence supports an edge/networked systems framing.

## Claims To Avoid

Do not write these as headline claims:

1. high automation or high automatic coverage
2. hardest cross-shift solved
3. `coverage-switch` is the best automatic detector
4. the new backbone is significantly better than every strong baseline on every metric
5. review is free
6. current evidence locks in `80%+` acceptance probability

## Main Tables

Use this table structure:

1. Main Table 1:
   safe auto backbone comparison using `cpd_shift_multiproto_consensus_plus`, `cpd_shift_consensus_plus`, `cpd_shift_multiproto_coverage_switch_plus`, `ova_gate`, `msp`, and `energy`
2. Main Table 2:
   deployment operating policy with `auto_coverage`, `actionable_coverage`, `safe_unknown_handling_rate`, `review_benign_rate`, and `final_defer_rate`
3. Main Table 3:
   review-load and deployment-cost table with per-1k queue sizes and throughput
4. Main Table 4:
   hardest protocol and threshold-sweep support

Appendix:

1. `triage_shift_multiproto_consensus_plus_ova_nonbenign`
2. `triage_shift_multiproto_consensus_gate_plus_ova_nonbenign`
3. `cpd_strict`, `cpd_adapt`, `cpd_adapt_consensus`
4. stress robustness digest
5. threshold sweep for `0.10`, `0.12`, and `0.14`

## Figures

Use these figures first:

1. system overview:
   safe auto backbone followed by deployment-time triage
2. operating frontier:
   `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/paper_operating_frontier.png`
3. hardest protocol case study:
   build from `hardest_cpd_consensus_protocols.csv` and `hardest_protocol_method_comparison.csv`
4. threshold-sweep or deployment-cost figure:
   derive from `paper_deployment_summary.csv` and `cov10/cov12/cov14`

## Reviewer-Facing Weak Points

These are the likely reviewer attacks and the intended response:

1. Why not just loosen the automatic threshold?
   Answer with the operating-frontier and the `coverage-switch` deployment-policy story.
2. Why is the auto backbone not the highest-coverage line?
   Answer that the paper optimizes for safe deployment and honest unknown handling, not automation.
3. Why is defer still large?
   Answer with the deployment-cost table and the explicit tradeoff between `actionable_coverage` and safe unknown handling.
4. What still fails?
   Answer with the hardest-protocol files and the limitations paragraph.
5. Why is this a WASA paper?
   Answer with the edge/networked deployment framing, runtime/queue metrics, and deployment-time triage abstraction.

## Submission Execution

Before final submission:

1. quote only numbers from the clean canonical digest
2. keep the stress digest in supplement only
3. write from `wasa_paper_draft_20260409.md`
4. build the bundle with the new docs and new config
5. verify that the bundle no longer includes the older `20260407` paper docs or reviewselector config

## Regeneration Command

Rebuild the canonical digest with:

```bash
cd ~/workspace/OpenFedBot
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
