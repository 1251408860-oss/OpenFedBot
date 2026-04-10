# WASA Paper Draft Skeleton

Date: 2026-04-09

This draft skeleton is anchored to the clean canonical digest:

- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z`

Use this file as the writing base for the WASA submission. The paper mainline is no longer the older review-selector framing. The stable story is:

1. `cpd_shift_multiproto_consensus_plus` as the safe auto backbone
2. `triage_shift_multiproto_coverage_switch_plus_ova_nonbenign` as the deployment operating policy
3. adaptive calibration-bank selection as a digest-time calibration policy
4. `actionable_coverage`, `safe_unknown_handling`, and low benign review burden as the deployment headline

## Candidate Title

Deployment-Safe Open-World Federated Bot Triage for Edge and Networked AI Threat Detection

## One-Sentence Positioning

`OpenFedBot` is not presented as a high-automation single-stage detector. It is presented as a deployment-oriented open-world federated triage system that combines a safe automatic backbone, adaptive calibration-bank selection, and a coverage-switch review policy that raises actionable coverage while keeping unknown routing safe and benign review load low.

## Abstract Draft

Open-world bot detection under federated and cross-scenario deployment must balance three competing goals: safe automatic acceptance, reliable handling of previously unseen traffic, and bounded analyst workload after distribution shift. We present `OpenFedBot`, a deployment-oriented open-world federated bot triage framework for edge and networked AI threat detection. The first layer, `cpd_shift_multiproto_consensus_plus`, uses multi-prototype open-world representation, agreement-based gating, and shift-aware reclamation to serve as a safe automatic backbone rather than an aggressive high-coverage detector. The second layer, `triage_shift_multiproto_coverage_switch_plus_ova_nonbenign`, conditionally switches to a more aggressive operating point only when protocol-level automatic coverage collapses, while routing the remaining deferred traffic through a low-benign review path. On the clean 10-seed canonical digest, the safe auto backbone reaches cross-scenario `coverage = 0.1513`, `selective_risk = 0.2398`, `unknown_misroute_rate = 0.0128`, and `accepted_benign_fpr = 0.000195`. The deployment operating policy lifts cross-scenario `actionable_coverage` to `0.4773` while preserving `safe_unknown_handling_rate = 0.9779` and `review_benign_rate = 0.0018`; under same-scenario deployment it reaches `actionable_coverage = 0.5793` with `safe_unknown_handling_rate = 0.9836`. Paired protocol analysis shows that the multi-prototype safe backbone is not a universal dominance claim over the older shift-consensus line, but it does deliver a statistically stronger benign false-alert profile, while the coverage-switch line belongs more naturally to deployment-time triage than to the primary automatic method. The hardest cross protocols remain unsolved at the automatic stage, yet triage materially improves their deployment usability. These results support a systems argument aligned with WASA: safe open-world federated triage is a better deployment abstraction for edge and networked threat detection than chasing high automatic acceptance alone.

## Contributions Draft

1. We formulate open-world federated bot detection as a deployment-time triage problem with three explicit outcomes: automatic accept, review, and final defer.
2. We introduce a multi-prototype safe automatic backbone, `cpd_shift_multiproto_consensus_plus`, that favors safer unknown routing and lower benign false alerts over aggressive automatic coverage.
3. We introduce a deployment operating policy, `triage_shift_multiproto_coverage_switch_plus_ova_nonbenign`, that activates a more aggressive operating point only when protocol-level safe coverage collapses.
4. We provide deployment-facing evidence beyond standard classification metrics, including review burden, defer burden, throughput, per-1k target cost, hardest-protocol analysis, and paired protocol statistics.
5. We make an honest systems claim: the hardest cross protocols remain a limitation, but the combined triage framework materially improves deployment usability while preserving high safe unknown handling.
6. We freeze the data-tooling interface through a local graph schema contract and a vendored Ca-Bench snapshot so the pipeline is reproducible without depending on an upstream moving target.

## Introduction Draft

Edge and networked AI threat-detection systems do not fail only because of closed-world classification error. They fail when previously unseen traffic is forced into known classes, when cross-scenario distribution shift collapses a nominally safe threshold, and when a deployment pipeline creates more analyst burden than it removes. This failure mode is particularly important in federated settings, where the model is trained across distributed graph views yet must still operate under open-world deployment conditions.

This paper therefore takes a systems view rather than a leaderboard view. The question is not whether a single automatic detector dominates every baseline on every metric. The question is whether a federated graph detector can be deployed with a safe automatic backbone, high safe unknown handling, bounded benign review burden, and measurable end-to-end operating value under same-scenario and cross-scenario shift. That is the design target of `OpenFedBot`.

The resulting claim is intentionally narrow and therefore more defensible. We do not claim that automatic coverage is already high in the most difficult cross-scenario protocols. We do not claim that the new backbone is significantly better than the older shift-consensus line on every metric. We instead show that a multi-prototype safe auto backbone is the more stable automatic method, that a coverage-switch triage policy is the stronger deployment operating point, and that the combined system raises actionable coverage to a usable range while keeping benign review burden very low.

To align with the WASA full-paper audience, write the framing explicitly around:

1. edge/cloud AI computing
2. smart networked applications
3. AI-based network threat detection
4. deployment-time operating policy under open-world shift

## Problem Setting

Define the deployment output space with three outcomes:

1. automatic accept:
   trusted output from the safe auto backbone
2. review:
   traffic routed to a second-stage analyzer
3. final defer:
   traffic still unresolved after review

The target metrics are:

1. `coverage`
2. `actionable_coverage`
3. `unknown_misroute_rate`
4. `accepted_benign_fpr`
5. `review_benign_rate`
6. `safe_unknown_handling_rate`
7. `final_defer_rate`

State clearly that `coverage` is only the first-stage automatic metric. The deployment-facing metric is `actionable_coverage`.

## Method Draft

### Stage 0: Adaptive Calibration-Bank Selection

The paper mainline still uses adaptive bank selection at digest time:

1. read `calibration_metrics.csv`
2. choose one bank per `(protocol, seed)`
3. maximize `cpd_val_coverage`
4. tie-break with minimum `cpd_val_risk`

Write this as a calibration policy that stabilizes the paper-facing digest. Do not oversell it as the primary algorithmic novelty.

### Stage 1: Safe Auto Backbone

The primary automatic method is `cpd_shift_multiproto_consensus_plus`.

Write it as a safe automatic backbone:

1. federated graph encoder produces logits and embeddings
2. multi-prototype representation provides class-wise local support instead of a single center
3. agreement-style gating keeps uncertain and likely unknown traffic out of unsafe auto acceptance
4. shift-aware reclaim operates conservatively and is not designed to maximize raw coverage

The key claim here is safety and stability, not high automation.

### Stage 2: Deployment Operating Policy

The deployment operating policy is `triage_shift_multiproto_coverage_switch_plus_ova_nonbenign`.

Write the policy in two parts:

1. default line:
   use the safer `cpd_shift_multiproto_consensus_plus`
2. conditional activation:
   when protocol-level safe auto coverage falls below `shift_hybrid_activation_coverage = 0.12`, switch to the more aggressive `cpd_shift_multiproto_consensus_gate_plus` operating point

This is the key distinction that must remain explicit in the paper:

1. `cpd_shift_multiproto_consensus_plus` is the safe auto backbone
2. `triage_shift_multiproto_coverage_switch_plus_ova_nonbenign` is the deployment operating policy
3. `cpd_shift_multiproto_coverage_switch_plus` is not the headline automatic detector

### Reproducibility Control

State these infrastructure decisions explicitly:

1. the local graph schema contract in `/home/user/workspace/OpenFedBot/docs/graph_schema_contract_v1.md`
2. the frozen builder snapshot in `/home/user/workspace/OpenFedBot/third_party/cabench_frozen`

## Experimental Setup Draft

Use the authoritative clean run:

- `/home/user/workspace/OpenFedBot/results/open_world_full_suite_multiproto_coverageswitch_clean_seed10_20260408T023210Z`

Use the authoritative clean digest:

- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z`

Use the stress digest only for supplement:

- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260408T034757Z`

Report:

1. same-scenario and cross-scenario results separately
2. 10 seeds
3. paired protocol-level statistics against `cpd_shift_consensus_plus`, `cpd_shift_multiproto_coverage_switch_plus`, and `cpd_shift_multiproto_consensus_gate_plus`
4. review-load and deployment-cost tables
5. threshold sweep comparison for `0.10`, `0.12`, and `0.14`
6. hardest-protocol breakdown

Main-table comparison rows:

1. `cpd_shift_multiproto_consensus_plus`
2. `cpd_shift_consensus_plus`
3. `cpd_shift_multiproto_coverage_switch_plus`
4. `ova_gate`
5. `msp`
6. `energy`

## Results Draft

### RQ1: Is the auto backbone safe enough to act as the paper mainline?

Use:

1. `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/paper_main_method_summary.csv`
2. `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/adaptive_paired_cpd_shift_multiproto_consensus_plus_vs_cpd_shift_consensus_plus_summary.csv`
3. `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/adaptive_paired_cpd_shift_multiproto_consensus_plus_vs_cpd_shift_multiproto_coverage_switch_plus_summary.csv`

Main statement:

1. cross `cpd_shift_multiproto_consensus_plus` reaches `coverage = 0.1513`, `selective_risk = 0.2398`, `unknown_misroute_rate = 0.0128`, and `accepted_benign_fpr = 0.000195`
2. same `cpd_shift_multiproto_consensus_plus` reaches `coverage = 0.2154`, `selective_risk = 0.0342`, `unknown_misroute_rate = 0.0164`, and `accepted_benign_fpr = 0.0000514`
3. versus `cpd_shift_consensus_plus`, the cleanest statistical gain is lower `accepted_benign_fpr` with `p = 0.015625`
4. versus `cpd_shift_multiproto_coverage_switch_plus`, the safe backbone gives lower average `unknown_misroute_rate`, but the win is not cleanly significant (`p = 0.125`), while `coverage` is intentionally lower (`p = 0.015625`)

Correct interpretation:

1. the multi-prototype line is a better safe backbone
2. it is not a universal headline win on every metric
3. the more aggressive coverage-switch line belongs in deployment policy, not as the main automatic method

### RQ2: Does the deployment policy raise actionable coverage without losing safe unknown handling?

Use:

1. `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/paper_main_triage_summary.csv`
2. `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/paper_review_load_summary.csv`
3. `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/paper_deployment_summary.csv`

Main statement:

1. cross `triage_shift_multiproto_coverage_switch_plus_ova_nonbenign` reaches `actionable_coverage = 0.4773`
2. cross `safe_unknown_handling_rate = 0.9779`
3. cross `review_benign_rate = 0.0018`
4. cross `final_defer_rate = 0.5227`
5. same `actionable_coverage = 0.5793`
6. same `safe_unknown_handling_rate = 0.9836`
7. same `review_benign_rate = 0.0015`

The correct systems story is:

1. the main gain is not “high automatic coverage”
2. the main gain is that actionable coverage reaches a paper-worthy deployment level while benign review burden stays very low

### RQ3: Is the deployment story strong enough for WASA?

Use:

1. `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/paper_deployment_summary.csv`
2. `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/paper_deployment_protocol_summary.csv`

State the deployment-cost numbers explicitly:

1. cross `review_queue_per_1k_targets = 298.82`
2. cross `defer_queue_per_1k_targets = 522.73`
3. cross `actionable_nodes_per_sec = 2342.69`
4. cross `end_to_end_sec_per_1k_targets = 0.2043`
5. same `review_queue_per_1k_targets = 342.53`
6. same `defer_queue_per_1k_targets = 420.70`
7. same `actionable_nodes_per_sec = 490.44`
8. same `end_to_end_sec_per_1k_targets = 1.2401`

Interpret these as deployment evidence for edge and networked applications. Do not mix in the stress-run deployment table.

### RQ4: What still fails?

Use:

1. `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/hardest_cpd_consensus_protocols.csv`
2. `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/hardest_triage_consensus_ova_protocols.csv`

Automatic-stage limitation:

1. `h_to_e_slowburn`: `coverage = 0.0771`, `selective_risk = 0.4342`, `unknown_misroute_rate = 0.0565`
2. `h_to_e_burst`: `coverage = 0.1152`, `selective_risk = 0.4553`, `unknown_misroute_rate = 0.0000`
3. `e_to_h_slowburn`: `coverage = 0.1575`, `selective_risk = 0.3621`, `unknown_misroute_rate = 0.0004`

Deployment-stage recovery:

1. `h_to_e_slowburn`: `actionable_coverage = 0.5798`, `review_coverage = 0.4269`, `safe_unknown_handling_rate = 0.9425`
2. `h_to_e_burst`: `actionable_coverage = 0.4382`, `review_coverage = 0.2865`, `safe_unknown_handling_rate = 0.9996`
3. `e_to_h_slowburn`: `actionable_coverage = 0.3897`, `review_coverage = 0.2194`, `safe_unknown_handling_rate = 0.9716`

Correct limitation statement:

1. hardest cross protocol remains unsolved at the automatic stage
2. the paper can honestly claim improved deployment usability, not solved cross-shift automation

### RQ5: Why keep `0.12` as the canonical threshold?

Use:

1. `/home/user/workspace/OpenFedBot/results/digest_cov10/reinforced_digest_20260408T040323Z`
2. `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z`
3. `/home/user/workspace/OpenFedBot/results/digest_cov14/reinforced_digest_20260408T040323Z`

Main statement:

1. `0.14` only raises cross `actionable_coverage` from `0.4773` to `0.4801`
2. the same change lowers cross `safe_unknown_handling_rate` from `0.9779` to `0.9610`
3. `0.10` does not add safety and lowers same-domain actionable coverage
4. therefore `shift_hybrid_activation_coverage = 0.12` remains the stable threshold

## Limitation Paragraph

This paragraph should appear in the main paper, not only in the appendix.

The most difficult cross-scenario transfers remain unsolved at the automatic stage. In the canonical clean digest, `h_to_e_slowburn` yields automatic `coverage = 0.0771` with `selective_risk = 0.4342`, while `h_to_e_burst` yields automatic `coverage = 0.1152` with `selective_risk = 0.4553`. These protocols therefore do not support a “hardest cross-shift solved” claim. The practical contribution is narrower: the system routes unknown traffic more safely than aggressive single-stage baselines, and the deployment operating policy recovers materially higher actionable coverage while keeping benign review burden low.

## Threats To Validity Draft

1. The evaluation is limited to the currently available scenario families and graph-construction pipeline.
2. Review-stage quality is measured offline rather than with live analyst interaction.
3. The adaptive selector depends on calibration-side metrics and may need revalidation under broader domains.
4. The hardest cross protocols show that a single deployment operating policy is not enough to eliminate all open-world failure modes.

## Claims To Avoid In The Paper

1. do not write that automation is already high
2. do not write that `coverage-switch` is the best automatic detector
3. do not write that hardest cross-shift is solved
4. do not write that the new backbone significantly dominates every strong baseline on every metric
5. do not quote stress-run deployment cost as real deployment runtime
6. do not claim `80%+` acceptance certainty from the current evidence

## Table Plan

1. Table 1:
   safe auto backbone comparison from `paper_main_method_summary.csv`
2. Table 2:
   deployment operating policy from `paper_main_triage_summary.csv`
3. Table 3:
   review load and deployment cost from `paper_review_load_summary.csv` and `paper_deployment_summary.csv`
4. Table 4:
   hardest protocol and threshold sweep support

## Figure Plan

1. system overview diagram:
   safe auto backbone + deployment-time triage
2. operating frontier:
   `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/paper_operating_frontier.png`
3. hardest protocol case study:
   `hardest_cpd_consensus_protocols.csv` plus `hardest_protocol_method_comparison.csv`
4. threshold-sweep figure:
   `cov10` vs `cov12` vs `cov14` cost/safety comparison

## Writing Order

Write in this order:

1. title and abstract
2. introduction and contributions
3. method section with the backbone/policy distinction made explicit
4. main results around actionable coverage and safe unknown handling
5. limitation paragraph
6. appendix comparisons and stress robustness
