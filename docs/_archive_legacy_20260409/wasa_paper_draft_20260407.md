# WASA Paper Draft Skeleton

Date: 2026-04-07

This draft skeleton is anchored to the authoritative digest:

- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z`

Use this file as the writing base for the WASA submission. The current mainline is the adaptive-bank full-suite digest, not the older fixed-`large` paper packet.

## Candidate Title

Conservative Open-World Federated Bot Detection with Adaptive Calibration and Selective Review over Cross-Scenario Graph Shifts

## One-Sentence Positioning

`OpenFedBot` is not presented as a universally dominant single-stage classifier. It is presented as a deployment-oriented open-world federated detection pipeline that keeps a conservative automatic gate, chooses calibration banks adaptively, and recovers practical coverage through a bounded selective review stage.

## Abstract Draft

Open-world bot detection in federated network environments must balance three competing goals: automatic coverage on known bot families, safe handling of previously unseen traffic, and bounded analyst workload under cross-scenario distribution shift. We present `OpenFedBot`, a deployment-oriented two-stage pipeline for federated graph-based bot detection. The first stage, `cpd_consensus_plus`, acts as a conservative automatic gate that routes most uncertain or unknown traffic to defer instead of misrouting it as known malicious traffic. We further replace the previous fixed `large` calibration bank with an adaptive bank-selection policy that chooses one bank per `(protocol, seed)` from calibration-side metrics by maximizing `cpd_val_coverage` and tie-breaking with minimum `cpd_val_risk`. The second stage, `triage_consensus_plus_prototype_or_ova_selective`, selectively reviews deferred traffic to recover actionable coverage without the benign-review explosion of earlier review paths. On the authoritative 10-seed full-suite evaluation, the automatic gate reduces cross-scenario unknown misroute rate to `0.0208` while keeping benign false alerts at `6.09` per `10k` benign flows. The full deployment policy lifts cross-scenario actionable coverage to `0.6781` with `0.9792` safe unknown handling and `0.1918` benign review rate. Relative to the fixed-`large` mainline, adaptive bank selection also improves the hardest `h_to_e_*` automatic transfers, raising `h_to_e_slowburn` coverage from `0.0564` to `0.0860` and `h_to_e_burst` from `0.0894` to `0.1236`, although these transfers remain unsolved. These results support a practical systems argument: in open-world federated deployment, safety-first automatic gating plus adaptive calibration and selective review is more robust than aggressively expanding single-stage acceptance.

## Contributions Draft

1. We formulate open-world federated bot detection as a deployment problem with explicit separation between automatic acceptance and selective review, rather than as a single-threshold closed-world classification problem.
2. We introduce `cpd_consensus_plus`, a conservative automatic gate that substantially reduces unknown misrouting and benign false alerts against `OVA`, `MSP`, and `Energy`.
3. We introduce an adaptive calibration-bank selection policy that improves the cross-scenario operating point and hardest-cross automatic frontier over the previous fixed `large` bank mainline.
4. We introduce `triage_consensus_plus_prototype_or_ova_selective`, a selective review policy that materially increases actionable coverage while sharply reducing benign review load relative to `triage_consensus_plus_ova`.
5. We provide a full-suite evaluation with cross-scenario and same-scenario breakdowns, paired statistical summaries, runtime and communication accounting, calibration-bank comparisons, and hardest-protocol analysis.
6. We freeze the data-tooling interface through a local graph schema contract and a vendored Ca-Bench builder snapshot so the experimental pipeline no longer depends on an upstream moving target.

## Introduction Draft

Open-world deployment is the actual failure mode for production bot detection. In practice, the detector does not only decide between benign traffic and previously seen bot families. It also encounters novel behaviors, scenario shifts, and protocol families whose feature geometry deviates from the training distribution. Under these conditions, a detector that maximizes raw automatic coverage often creates the wrong system-level behavior: it misroutes unknown traffic into known malicious classes or generates analyst load that scales poorly with benign traffic.

This paper takes a systems view. The question is not whether a single confidence rule can dominate every baseline on every metric. The question is whether a federated graph detector can be deployed with a conservative automatic stage, predictable unknown handling, a stable calibration policy, and a review stage that meaningfully recovers operational coverage without overwhelming analysts. That is the design target of `OpenFedBot`.

The resulting argument is intentionally narrow and therefore stronger. We do not claim that automatic coverage is already high in the most difficult cross-scenario protocols. We instead show that a conservative gate can keep unknown routing safe, that adaptive calibration improves the deployment operating point over the old fixed-bank default, and that a selective review layer can recover a large portion of deferred traffic at much lower benign review cost than the previous review path.

## Problem Setting

Define the deployment objective using three outputs:

1. automatic accept:
   known bot family accepted directly by the gate
2. review:
   uncertain traffic sent to the second-stage analyzer
3. defer:
   traffic still unresolved after review

The target metrics are:

1. `coverage` / `actionable_coverage`
2. `unknown_misroute_rate`
3. `accepted_benign_fpr`
4. `review_benign_rate`
5. `safe_unknown_handling_rate`

State explicitly that `actionable_coverage` is the deployment-facing metric, while `coverage` is only the first-stage automatic metric.

## Method Draft

### Stage 0: Adaptive Calibration-Bank Selection

Before presenting the automatic gate, state the calibration policy clearly:

1. each `(protocol, seed)` already emits calibration-side metrics for the available banks
2. the digest chooses one bank by maximizing `cpd_val_coverage`
3. ties are broken by minimizing `cpd_val_risk`
4. the resulting assignments are frozen in `selected_bank_assignments.csv`

Write this as a deployment-facing calibration policy, not as a new target-time model adaptation claim.

### Stage 1: Conservative Automatic Gate

The primary automatic method is `cpd_consensus_plus`.

Write it as a conservative agreement-based gate:

1. federated graph encoder produces node embeddings and class scores
2. calibrated confidence and prototype-distance signals must agree
3. only high-confidence known samples are accepted automatically
4. uncertain and likely unknown samples are deferred

The key claim here is safety, not maximal automation.

### Stage 2: Selective Review

The main deployment policy is `triage_consensus_plus_prototype_or_ova_selective`.

Its review path is `review_prototype_or_ova_selective`, which combines:

1. `prototype_only_nonbenign`
2. `ova_gate_selective`

Write this as a two-part review recovery mechanism:

1. a low-benign prototype path recovers deferred non-benign samples with better precision
2. a budgeted OVA-style recovery path is only activated selectively, so it does not recreate the old benign-review explosion

### Reproducibility Control

State two infrastructure decisions explicitly:

1. the local graph schema contract in `/home/user/workspace/OpenFedBot/docs/graph_schema_contract_v1.md`
2. the frozen builder snapshot in `/home/user/workspace/OpenFedBot/third_party/cabench_frozen`

This strengthens the systems-paper story because the pipeline no longer depends on a mutable upstream `main` branch.

## Experimental Setup Draft

Use the authoritative run:

- `/home/user/workspace/OpenFedBot/results/open_world_full_suite_reviewselector_seed10_20260407T060213Z`

Use the authoritative digest:

- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z`

Report:

1. same-scenario and cross-scenario results separately
2. 10 seeds
3. paired protocol-level statistics for `OVA`, `MSP`, `Energy`, and `cpd_consensus`
4. runtime and communication costs
5. fixed-`large` vs adaptive calibration-bank comparison
6. hardest-protocol breakdown

Baselines in the main table:

1. `ova_gate`
2. `msp`
3. `energy`
4. `cpd_consensus`

## Results Draft

### RQ1: Does the automatic gate improve safety?

Use `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/paper_main_method_summary.csv`.

Main statement:

1. cross-scenario `cpd_consensus_plus` reaches `unknown_misroute_rate = 0.0208`
2. cross-scenario `accepted_benign_fpr = 0.0006087`, which is `6.09` alerts per `10k` benign samples
3. cross-scenario `coverage = 0.1485`
4. same-scenario `cpd_consensus_plus` keeps `unknown_misroute_rate = 0.0231` with `coverage = 0.2091`

Paired support against the true headline baselines:

1. vs `OVA`, unknown misroute improves by `0.5218` average protocol benefit, `p = 0.00048828125`
2. vs `MSP`, unknown misroute improves by `0.5705`, `p = 0.00048828125`
3. vs `Energy`, unknown misroute improves by `0.5517`, `p = 0.00048828125`
4. benign false alerts are also lower with paired support against `OVA`, `MSP`, and `Energy`

Nuance against `cpd_consensus`:

1. `coverage` improves with `p = 0.00048828125`
2. `selective_risk` improves with `p = 0.03857421875`
3. `accepted_known_macro_f1` improves with `p = 0.00634765625`
4. `unknown_misroute_rate` is not a clean headline win, `p = 0.0625`

Do not headline `coverage` as “high.” The correct framing is safer automatic acceptance under conservative coverage.

### RQ2: Does adaptive calibration improve the paper mainline?

Use:

1. `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/adaptive_bank_method_summary.csv`
2. `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/clean_large_method_summary.csv`
3. `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/selected_bank_assignments.csv`

Main statement:

1. the selector does not collapse to fixed `large`; it chooses `medium 45`, `large 40`, and `small 35` times across the 120 `(protocol, seed)` cases
2. cross `cpd_consensus_plus` coverage improves from `0.1402` to `0.1485`
3. cross selective risk improves from `0.2765` to `0.2326`
4. cross benign alerts improve from `6.56` to `6.09` per `10k`
5. the hardest `h_to_e_slowburn` and `h_to_e_burst` transfers both improve materially

This section justifies replacing fixed `large` as the paper mainline calibration policy.

### RQ3: Does selective review recover practical coverage without exploding analyst load?

Use `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/paper_main_triage_summary.csv`.

Main statement:

1. cross-scenario `triage_consensus_plus_prototype_or_ova_selective` reaches `actionable_coverage = 0.6781`
2. cross-scenario `safe_unknown_handling_rate = 0.9792`
3. cross-scenario `review_benign_rate = 0.1918`
4. same-scenario `actionable_coverage = 0.7665`

Contrast against the previous review path under the same adaptive digest:

1. `triage_consensus_plus_ova` cross `actionable_coverage = 0.6316`
2. `triage_consensus_plus_ova` cross `review_benign_rate = 0.4323`
3. the new main policy improves actionable coverage and sharply reduces benign review burden at the same time

This is the strongest deployment-facing result in the paper. Make it the center of the main results section.

### RQ4: Is the system lightweight enough for an edge deployment story?

Use `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/paper_runtime_summary.csv`.

State the mean cross-scenario costs:

1. `total_runtime_sec = 2.1025`
2. `total_comm_mb = 0.8686`
3. `model_size_mb = 0.0106`
4. `rounds_completed = 5`

These numbers support a practical deployment story rather than a heavyweight retraining story.

## Limitation Paragraph

This paragraph should appear directly in the main paper, not only in the appendix.

The most difficult cross-scenario transfers remain unsolved at the automatic stage. In the authoritative adaptive full-suite run, `h_to_e_slowburn` yields automatic `coverage = 0.0860` with `selective_risk = 0.5040`, and `h_to_e_burst` yields automatic `coverage = 0.1236` with `selective_risk = 0.4938`. These values are materially better than the fixed-`large` mainline, but they are still far from a solved automatic-acceptance regime. We therefore do not claim that the automatic gate solves extreme cross-scenario shift. The practical contribution is narrower: the system keeps these cases out of unsafe automatic acceptance more reliably than the previous mainline and recovers a large portion of them through selective review.

## Threats To Validity Draft

1. The evaluation is limited to the available scenario families and graph construction pipeline.
2. Review-stage quality is measured by offline labels rather than a live analyst study.
3. The adaptive selector depends on the emitted calibration-side metrics and may need revalidation under additional domains.
4. The hardest `h_to_e_*` shifts indicate that a single calibration policy is insufficient to eliminate all open-world failure modes.

## Claims To Avoid In The Paper

1. do not write that automatic coverage is already high
2. do not write that adaptive calibration solves hardest cross protocols
3. do not write that `cpd_consensus_plus` is better than `cpd_consensus` on every metric
4. do not write that selective risk is universally significant against every baseline
5. do not frame the review stage as free or zero-cost
6. do not promote `hybrid pseudo` beyond appendix ablations

## Table Plan

1. Table 1:
   automatic gate comparison using `paper_main_method_summary.csv`
2. Table 2:
   adaptive calibration comparison using `adaptive_bank_method_summary.csv` and `clean_large_method_summary.csv`
3. Table 3:
   deployment policy comparison using `paper_main_triage_summary.csv` and `adaptive_bank_triage_summary.csv`
4. Table 4:
   review load and runtime using `paper_review_load_summary.csv` and `paper_runtime_summary.csv`

## Figure Plan

1. system overview diagram
2. operating frontier plot:
   `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z/paper_operating_frontier.png`
3. hardest-protocol case study:
   `hardest_cpd_consensus_protocols.csv` plus `hardest_protocol_method_comparison.csv`
4. adaptive-bank selection summary:
   derive a simple figure from `selected_bank_assignments.csv`

## Writing Order

Write in this order:

1. abstract
2. introduction
3. method
4. results
5. limitation and threats to validity
6. conclusion

Do not start from the related-work section. Lock the core empirical story first.
