# WASA Full Paper Writing Blueprint

Date: 2026-04-09

This document is the detailed writing blueprint for the current `OpenFedBot` WASA paper. It is not a replacement for the paper draft skeleton. It is the operational guide for turning the current code, digest, figures, and tables into a coherent full-paper manuscript.

The writing base remains:

- `/home/user/workspace/OpenFedBot/docs/wasa_paper_draft_20260409.md`

The single source of truth for main-paper numbers remains:

- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z`

The current four main figures remain:

- `/home/user/workspace/OpenFedBot/results/wasa_main_figures_20260409T023651Z/fig1_openfedbot_system_overview.png`
- `/home/user/workspace/OpenFedBot/results/wasa_main_figures_20260409T023651Z/fig2_safe_auto_backbone_evidence.png`
- `/home/user/workspace/OpenFedBot/results/wasa_main_figures_20260409T023651Z/fig3_deployment_and_hardest_protocols.png`
- `/home/user/workspace/OpenFedBot/results/wasa_main_figures_20260409T023651Z/fig4_threshold_selection.png`

## 1. What Paper This Is

This paper should be written as a deployment-oriented systems paper for edge and networked AI threat detection.

It should not be written as:

1. a high-automation single-stage classifier paper
2. a universal state-of-the-art open-world detector paper
3. a broad cross-dataset generalization paper

It should be written as:

1. a deployment-safe open-world federated bot triage framework
2. a two-layer system with a safe auto backbone plus a deployment operating policy
3. an honest systems paper that raises actionable coverage while keeping unknown routing safe and benign review burden low

The core distinction that must remain explicit everywhere is:

1. `cpd_shift_multiproto_consensus_plus` = safe auto backbone
2. `triage_shift_multiproto_coverage_switch_plus_ova_nonbenign` = deployment operating policy
3. `actionable_coverage` = deployment-facing metric
4. `coverage` = first-stage automatic metric only

## 2. The One-Sentence Story

Use this as the paper's internal compass:

`OpenFedBot` is a deployment-oriented open-world federated bot triage system that uses a conservative multi-prototype automatic backbone and a coverage-switch review policy to raise actionable coverage under scenario shift while keeping unknown routing safe and benign review burden low.

Shorter version for repeated use:

`OpenFedBot` is not a high-automation detector. It is a safer deployment stack.

## 3. The Strongest Claims

These are the claims the current evidence can support:

1. The multi-prototype line is a safer automatic backbone than the more aggressive deployment-time operating line.
2. The deployment operating policy raises cross-scenario `actionable_coverage` to a usable range while keeping `safe_unknown_handling_rate` high.
3. The benign review burden is low enough to support a real deployment story.
4. The hardest cross protocols remain difficult at the automatic stage, but triage materially improves deployment usability.
5. The paper's value is in safe deployment behavior, not in maximizing raw automatic coverage.

These are claims the paper should not make:

1. high automation
2. hardest cross-shift solved
3. universal metric dominance over all baselines
4. multiple independent public datasets
5. broad real-world generalization beyond the evaluated benchmark family

## 4. Dataset Wording That Will Not Get You Attacked

The dataset wording matters because the current experiments do not span multiple unrelated benchmark families.

What you actually used:

1. two `Ca-Bench` graph scenarios from an unpublished benchmark paper under submission
2. `scenario_e_three_tier_high2_public_data_v1`
3. `scenario_h_mimic_heavy_overlap_public_data_v1`
4. three bot families: `burst`, `slowburn`, `mimic`
5. `12` leave-one-family-out protocols
6. same-scenario and cross-scenario evaluation
7. `10` random seeds

Do not write:

1. `multiple public datasets`
2. `extensive cross-dataset evaluation`
3. `broad benchmark diversity`

Write instead:

> We evaluate OpenFedBot on two `Ca-Bench` graph scenarios, `scenario_e_three_tier_high2` and `scenario_h_mimic_heavy_overlap`, from an unpublished benchmark paper currently under submission, under leave-one-family-out open-world protocols over three bot families (`burst`, `slowburn`, and `mimic`) with both same-scenario and cross-scenario evaluation.

Useful supporting facts if the experimental setup section needs more specificity:

1. `scenario_e`: `5976` nodes, `8142` edges, `81` source IPs
2. `scenario_h`: `6985` nodes, `9755` edges, `90` source IPs
3. both are local graph assets built from the frozen `Ca-Bench` snapshot

## 5. Recommended Paper Structure

Use this manuscript structure unless you are forced to compress heavily:

1. Title
2. Abstract
3. Introduction
4. Problem Setting And System Overview
5. Method
6. Experimental Setup
7. Results
8. Discussion And Limitations
9. Related Work
10. Conclusion

If space is tight, merge `Problem Setting And System Overview` into `Method`, and keep `Related Work` short.

## 6. Section-By-Section Blueprint

## 6.1 Title

Recommended title direction:

1. deployment-safe
2. open-world
3. federated
4. bot triage
5. edge or networked AI threat detection

Best current title:

`Deployment-Safe Open-World Federated Bot Triage for Edge and Networked AI Threat Detection`

Acceptable alternates:

1. `OpenFedBot: Deployment-Safe Open-World Federated Bot Triage for Edge and Networked Threat Detection`
2. `Safe Open-World Federated Bot Triage Under Scenario Shift`
3. `Deployment-Oriented Open-World Federated Bot Triage with Safe Unknown Routing`

## 6.2 Abstract

The abstract should have exactly five moves:

1. define the deployment problem
2. explain why pure automatic coverage is the wrong target
3. describe the two-layer system
4. report the strongest clean numbers
5. close with the honest claim and limitation boundary

### Abstract Content Checklist

The abstract must include:

1. federated setting
2. open-world shift
3. safe auto backbone
4. deployment operating policy
5. `actionable_coverage`
6. `safe_unknown_handling_rate`
7. low `review_benign_rate`
8. hardest cross protocols remain unsolved at the automatic stage

### Abstract Draft You Can Start From

Open-world bot detection under federated and cross-scenario deployment must balance three competing goals: safe automatic acceptance, reliable handling of previously unseen traffic, and bounded analyst workload after distribution shift. We present `OpenFedBot`, a deployment-oriented open-world federated bot triage framework for edge and networked AI threat detection. The first layer, `cpd_shift_multiproto_consensus_plus`, uses multi-prototype open-world representation, agreement-based gating, and shift-aware reclamation to serve as a safe automatic backbone rather than an aggressive high-coverage detector. The second layer, `triage_shift_multiproto_coverage_switch_plus_ova_nonbenign`, conditionally switches to a more aggressive operating point only when protocol-level automatic coverage collapses, while routing the remaining deferred traffic through a low-benign review path. On the clean canonical digest, the safe auto backbone reaches cross-scenario `coverage = 0.1513`, `selective_risk = 0.2398`, `unknown_misroute_rate = 0.0128`, and `accepted_benign_fpr = 0.000195`. The deployment operating policy lifts cross-scenario `actionable_coverage` to `0.4773` while preserving `safe_unknown_handling_rate = 0.9779` and `review_benign_rate = 0.0018`; under same-scenario deployment it reaches `actionable_coverage = 0.5793` with `safe_unknown_handling_rate = 0.9836`. The hardest cross protocols remain unsolved at the automatic stage, yet triage materially improves their deployment usability. These results support a systems argument aligned with WASA: safe open-world federated triage is a stronger deployment abstraction for edge and networked threat detection than chasing high automatic acceptance alone.

## 6.3 Introduction

The introduction should be four paragraphs plus a contributions block.

### Paragraph 1: Real Problem

Goal:

Explain that deployment failure is caused by unsafe unknown routing and review overload, not only by closed-world classification error.

What to say:

1. open-world deployment produces unknown traffic
2. scenario shift breaks static thresholds
3. unsafe auto acceptance is costly
4. review overload is also a systems failure

Useful sentence stem:

> In federated bot detection, deployment failure arises not only from misclassification of known traffic, but also from unsafe routing of previously unseen traffic and from analyst burden created by distribution shift.

### Paragraph 2: Gap In Prior Framing

Goal:

Say that many methods optimize for automatic detection quality, but that is not enough for real deployment.

What to say:

1. prior open-world work often optimizes a detector
2. prior federated work often optimizes training robustness
3. neither directly answers deployment-time workflow design
4. the missing abstraction is triage

Useful sentence stem:

> Existing open-world and federated detection pipelines typically focus on the detector itself, whereas deployment requires a workflow that decides what to accept automatically, what to send for review, and what to defer safely.

### Paragraph 3: Your System

Goal:

Introduce the two-layer stack and the main design philosophy.

What to say:

1. safe auto backbone
2. deployment operating policy
3. conservative by design
4. deployment value comes from actionable coverage, not pure auto coverage

Useful sentence stem:

> We therefore formulate the problem as deployment-safe open-world federated triage and build a two-layer system: a conservative automatic backbone for safe unknown handling, followed by a coverage-switch operating policy that increases actionable coverage when the automatic line becomes too brittle.

### Paragraph 4: Honest Scope

Goal:

Pre-empt reviewer attacks by being precise about what is and is not solved.

What to say:

1. not a high-automation claim
2. not a universal dominance claim
3. hardest cross protocols remain hard
4. still useful because deployment usability improves materially

Useful sentence stem:

> Our claim is intentionally narrower than a leaderboard claim: the hardest cross-scenario protocols remain unsolved at the automatic stage, but the combined triage stack delivers a substantially stronger deployment tradeoff between actionable coverage, safe unknown handling, and benign review burden.

### Contributions Block

Keep it to four or five bullets only.

Recommended contribution bullets:

1. We formulate federated open-world bot detection as a deployment-time triage problem with automatic accept, review, and final defer outcomes.
2. We introduce `cpd_shift_multiproto_consensus_plus` as a safe automatic backbone built around multi-prototype open-world representation and conservative shift-aware gating.
3. We introduce `triage_shift_multiproto_coverage_switch_plus_ova_nonbenign`, a deployment operating policy that conditionally activates a more aggressive line only when protocol-level safe coverage collapses.
4. We report deployment-facing evidence beyond standard classification metrics, including actionable coverage, benign review burden, per-1k queue cost, throughput, and hardest-protocol behavior.
5. We provide an honest evaluation boundary: the hardest cross protocols remain a limitation, but the triage stack materially improves deployment usability under scenario shift.

## 6.4 Problem Setting And System Overview

This section should be short and formal.

Define:

1. source scenario
2. target scenario
3. same-scenario vs cross-scenario
4. known families
5. holdout family as open-world unknown
6. three deployment outcomes: auto accept, review, final defer

Use `Figure 1` here.

What the text around `Figure 1` should do:

1. explain the pipeline
2. explain the separation between backbone and policy
3. state why `actionable_coverage` is more important than raw `coverage`

Useful paragraph skeleton:

> Figure 1 summarizes the canonical deployment stack. OpenFedBot first applies a conservative automatic backbone, `cpd_shift_multiproto_consensus_plus`, to accept only traffic that passes safe open-world gating. Deferred traffic is then handled by the deployment policy `triage_shift_multiproto_coverage_switch_plus_ova_nonbenign`, which selectively switches to a more aggressive operating line only when protocol-level automatic coverage falls below the canonical threshold. This separation allows the paper to distinguish first-stage automatic safety from deployment-time workflow value.

## 6.5 Method

Do not write the method as one long block. Use three subsections.

### Method Subsection A: Federated Graph Backbone

Keep this concise.

Say:

1. GraphSAGE encoder
2. FedAvg training
3. topology-noniid client partition
4. target-time pseudo adaptation exists, but do not oversell it over the main story

### Method Subsection B: Safe Auto Backbone

This is where you explain `cpd_shift_multiproto_consensus_plus`.

Explain:

1. class-wise multi-prototype bank
2. agreement-style gating or consensus gating
3. shift-aware reclaim
4. conservative operating philosophy

Important wording:

1. `safer`
2. `more stable`
3. `conservative`
4. `backbone`

Avoid wording:

1. `best detector`
2. `highest coverage`
3. `dominates all baselines`

### Method Subsection C: Deployment Operating Policy

This subsection is critical.

Explain:

1. default to safe backbone
2. detect coverage collapse at protocol level
3. switch to more aggressive auto line only when needed
4. use `OVA` non-benign review path
5. output one of three deployment outcomes

Write this subsection as policy logic, not as a classifier detail.

### Method Subsection D: Adaptive Calibration-Bank Selection

Keep this explicit but modest.

State:

1. it is a digest-time calibration policy
2. per `(protocol, seed)` choose one bank
3. maximize `cpd_val_coverage`
4. tie-break by minimum `cpd_val_risk`

Do not oversell it as the main novelty.

## 6.6 Experimental Setup

This section should be crisp, reproducible, and reviewer-proof.

### Dataset Paragraph

Use the exact benchmark-scoped wording from Section 4.

### Protocol Paragraph

State:

1. `12` protocols
2. `6` same-scenario protocols
3. `6` cross-scenario protocols
4. leave-one-family-out over `burst`, `slowburn`, `mimic`
5. same-scenario target mode uses temporal test
6. cross-scenario target mode evaluates all target flow nodes

### Training Paragraph

State the minimal reproducibility facts:

1. GraphSAGE + FedAvg
2. `10` clients
3. topology-noniid partition
4. `10` seeds: `11, 17, 23, 42, 58, 64, 73, 84, 95, 111`
5. hidden size `32`
6. `5` rounds
7. `1` local epoch per round
8. `lr = 0.01`

### Baselines Paragraph

Separate automatic baselines and deployment policies.

Automatic baselines in the main table:

1. `cpd_shift_multiproto_consensus_plus`
2. `cpd_shift_consensus_plus`
3. `cpd_shift_multiproto_coverage_switch_plus`
4. `ova_gate`
5. `msp`
6. `energy`

Main deployment policy:

1. `triage_shift_multiproto_coverage_switch_plus_ova_nonbenign`

Appendix policies:

1. `triage_shift_multiproto_consensus_plus_ova_nonbenign`
2. `triage_shift_multiproto_consensus_gate_plus_ova_nonbenign`

### Metrics Paragraph

Define the following clearly:

1. `coverage`
2. `selective_risk`
3. `unknown_misroute_rate`
4. `accepted_benign_fpr`
5. `actionable_coverage`
6. `safe_unknown_handling_rate`
7. `review_benign_rate`
8. `final_defer_rate`
9. throughput and queue cost metrics

State explicitly:

> `coverage` measures first-stage automatic acceptance, whereas `actionable_coverage` measures the fraction of target traffic resolved through either automatic acceptance or review and is therefore the deployment-facing metric.

## 6.7 Results

Write the results as four research questions. This is cleaner than a generic subsection list.

### RQ1. Is The Automatic Backbone Safe Enough To Be The Mainline?

Use:

1. `Figure 2`
2. `paper_main_method_summary.csv`
3. paired summaries against `cpd_shift_consensus_plus`
4. paired summaries against `cpd_shift_multiproto_coverage_switch_plus`

Must-report numbers:

1. cross `coverage = 0.1513`
2. cross `selective_risk = 0.2398`
3. cross `unknown_misroute_rate = 0.0128`
4. cross `accepted_benign_fpr = 0.000195`
5. same `coverage = 0.2154`
6. same `selective_risk = 0.0342`
7. same `unknown_misroute_rate = 0.0164`
8. same `accepted_benign_fpr = 0.0000514`

Correct interpretation:

1. this is a safe backbone
2. it is not a high-coverage headline
3. the cleanest statistical gain over the older shift-consensus line is lower `accepted_benign_fpr`
4. the more aggressive coverage-switch line belongs in deployment policy, not as the main automatic headline

Paired-statistics sentences that are worth writing:

1. Against `cpd_shift_consensus_plus`, the clearest paired improvement is lower `accepted_benign_fpr` with sign test `p = 0.015625`, while gains in `coverage` and `unknown_misroute_rate` are not cleanly significant (`p = 0.3877` and `p = 0.7266`).
2. Against `cpd_shift_multiproto_coverage_switch_plus`, the safe backbone reduces average `unknown_misroute_rate`, but the difference is not cleanly significant (`p = 0.125`); as expected, the aggressive line achieves higher `coverage` (`p = 0.015625`), which is why it is treated as a deployment operating point rather than the main automatic method.

### RQ2. Does The Deployment Policy Improve Usability Without Breaking Safety?

Use:

1. `Figure 3A`
2. `paper_main_triage_summary.csv`

Must-report numbers:

1. cross `actionable_coverage = 0.4773`
2. cross `auto_coverage = 0.1784`
3. cross `review_coverage = 0.2988`
4. cross `safe_unknown_handling_rate = 0.9779`
5. cross `review_benign_rate = 0.0018`
6. cross `final_defer_rate = 0.5227`
7. same `actionable_coverage = 0.5793`
8. same `auto_coverage = 0.2368`
9. same `review_coverage = 0.3425`
10. same `safe_unknown_handling_rate = 0.9836`
11. same `review_benign_rate = 0.0015`
12. same `final_defer_rate = 0.4207`

Correct interpretation:

1. the paper's main gain is not higher automatic coverage
2. the paper's main gain is usable deployment resolution after review recovery
3. safe unknown handling remains high
4. benign review burden remains low

Useful sentence stem:

> The deployment policy raises cross-scenario actionable coverage from a conservative automatic base to `0.4773` while preserving `0.9779` safe unknown handling and holding the benign review rate to `0.0018`, indicating that the improvement is not purchased through unsafe routing or uncontrolled analyst burden.

### RQ3. Is The Deployment Story Strong Enough For A Systems Venue?

Use:

1. `Figure 3B`
2. `paper_deployment_summary.csv`

Must-report numbers:

1. cross `review_queue_per_1k_targets = 298.82`
2. cross `defer_queue_per_1k_targets = 522.73`
3. cross `actionable_nodes_per_sec = 2342.69`
4. cross `end_to_end_sec_per_1k_targets = 0.2043`
5. same `review_queue_per_1k_targets = 342.53`
6. same `defer_queue_per_1k_targets = 420.70`
7. same `actionable_nodes_per_sec = 490.44`
8. same `end_to_end_sec_per_1k_targets = 1.2401`

Correct interpretation:

1. this is workload shaping evidence
2. this supports the edge/networked systems story
3. do not call it low defer
4. call it explicit and bounded deployment tradeoff accounting

Useful sentence stem:

> The deployment contribution is therefore best understood as workload shaping rather than automation completion: the system exposes how much traffic is resolved automatically, how much enters review, how much remains deferred, and what queue cost and throughput this induces under same- and cross-scenario deployment.

### RQ4. What Still Fails, And Why Is The System Still Worth Writing?

Use:

1. `Figure 3C`
2. `Figure 3D`
3. `hardest_cpd_consensus_protocols.csv`
4. `hardest_triage_consensus_ova_protocols.csv`

Automatic-stage limitation numbers:

1. `h_to_e_slowburn`: `coverage = 0.0771`, `selective_risk = 0.4342`, `unknown_misroute_rate = 0.0565`
2. `h_to_e_burst`: `coverage = 0.1152`, `selective_risk = 0.4553`, `unknown_misroute_rate = 0.0000`
3. `e_to_h_slowburn`: `coverage = 0.1575`, `selective_risk = 0.3621`, `unknown_misroute_rate = 0.0004`

Deployment-stage recovery numbers:

1. `e_to_h_slowburn`: `actionable_coverage = 0.3897`, `review_coverage = 0.2194`, `safe_unknown_handling_rate = 0.9716`
2. `h_to_e_burst`: `actionable_coverage = 0.4382`, `review_coverage = 0.2865`, `safe_unknown_handling_rate = 0.9996`
3. `h_to_e_slowburn` should be cited from the canonical summary used earlier: `actionable_coverage = 0.5798`, `review_coverage = 0.4269`, `safe_unknown_handling_rate = 0.9425`

Correct interpretation:

1. hardest cross protocols remain unsolved automatically
2. triage still materially improves deployment usability
3. this becomes a limitation plus value argument, not a solved-problem argument

This paragraph matters. Do not hide the failure cases.

## 6.8 Threshold Selection Section

This can be a short subsection in results or a short subsection in discussion.

Use:

1. `Figure 4`
2. `digest_cov10`
3. `digest_cov12`
4. `digest_cov14`

Must-report numbers:

1. `cov10` cross `actionable_coverage = 0.4761`, cross `safe_unknown_handling = 0.9780`, same `actionable_coverage = 0.5753`
2. `cov12` cross `actionable_coverage = 0.4773`, cross `safe_unknown_handling = 0.9779`, same `actionable_coverage = 0.5793`
3. `cov14` cross `actionable_coverage = 0.4801`, cross `safe_unknown_handling = 0.9610`, same `actionable_coverage = 0.5810`

Correct interpretation:

1. `0.14` buys little coverage
2. `0.14` costs visible safety
3. `0.10` does not provide a compensating gain
4. `0.12` remains the most stable canonical threshold

Good sentence:

> We keep `shift_hybrid_activation_coverage = 0.12` as the canonical threshold because `0.14` yields only marginal coverage gains while causing a visible drop in cross-scenario safe unknown handling.

## 6.9 Discussion And Limitations

This section should be explicit, not defensive.

The section should say:

1. only two `Ca-Bench` scenarios from the current benchmark submission were evaluated
2. claims are benchmark-scoped, not broad cross-dataset generalization claims
3. hardest cross protocols remain unsolved at the automatic stage
4. final defer remains substantial in difficult settings
5. the main value is safer deployment workflow, not elimination of uncertainty

Useful sentence stem:

> The present evaluation supports a benchmark-scoped deployment claim rather than a universal generalization claim. In particular, the hardest cross-scenario protocols still produce low automatic coverage and substantial final defer, which means the current system should be understood as a safer triage framework rather than a solved high-automation detector.

## 6.10 Related Work

Keep related work focused on three lines only:

1. open-world and selective classification for unknown-aware detection
2. federated and graph-based bot or anomaly detection
3. human-in-the-loop triage, selective abstention, or deployment-safe AI systems

What related work should do:

1. create the space your paper sits in
2. show why the combination of federated graph detection and deployment triage is different
3. avoid a long laundry list

One useful contrast sentence:

> Unlike work that optimizes a single detector under open-world uncertainty, our focus is the deployment-time workflow that separates safe automatic acceptance from review and defer decisions under scenario shift.

## 6.11 Conclusion

The conclusion should be short and disciplined.

It should restate:

1. open-world federated bot detection should be framed as deployment-safe triage
2. the multi-prototype line is a safe backbone
3. the coverage-switch policy improves deployment usability
4. hardest cross protocols remain a limitation
5. future work should target stronger guarantees and harder-shift recovery

## 7. Figures And Tables Map

Use this mapping unless layout forces small changes.

### Main Figures

1. `Figure 1`: system overview
   Purpose: establish the stack and the deployment framing
2. `Figure 2`: safe auto backbone evidence
   Purpose: justify why `cpd_shift_multiproto_consensus_plus` is the main automatic line
3. `Figure 3`: deployment value and hardest protocols
   Purpose: show actionable coverage, queue cost, and honest hardest-case recovery
4. `Figure 4`: threshold selection
   Purpose: defend `0.12` as the canonical operating point

### Main Tables

1. Table 1: automatic backbone comparison
2. Table 2: deployment operating policy summary
3. Table 3: review-load and deployment-cost summary
4. Table 4: hardest-protocol and threshold-support table

If one table must move to appendix, move the threshold-support table first.

## 8. Exact Numbers Worth Quoting In Main Text

These are the safest headline numbers.

### Backbone

1. cross `coverage = 0.1513`
2. cross `unknown_misroute_rate = 0.0128`
3. cross `accepted_benign_fpr = 0.000195`
4. same `coverage = 0.2154`
5. same `unknown_misroute_rate = 0.0164`
6. same `accepted_benign_fpr = 0.0000514`

### Deployment

1. cross `actionable_coverage = 0.4773`
2. cross `safe_unknown_handling_rate = 0.9779`
3. cross `review_benign_rate = 0.0018`
4. same `actionable_coverage = 0.5793`
5. same `safe_unknown_handling_rate = 0.9836`
6. same `review_benign_rate = 0.0015`

### Statistics

1. benign FPR improvement over `cpd_shift_consensus_plus`: `p = 0.015625`
2. coverage difference vs `cpd_shift_consensus_plus`: `p = 0.3877`
3. unknown misroute difference vs `cpd_shift_consensus_plus`: `p = 0.7266`
4. unknown misroute difference vs `cpd_shift_multiproto_coverage_switch_plus`: `p = 0.125`
5. coverage tradeoff vs `cpd_shift_multiproto_coverage_switch_plus`: `p = 0.015625`

## 9. Claims To Repeat Consistently

The following sentences should appear in some form in the abstract, introduction, method, results, and conclusion:

1. `OpenFedBot` is written as a deployment-safe triage framework, not as a high-automation detector.
2. `cpd_shift_multiproto_consensus_plus` is the safe auto backbone.
3. `triage_shift_multiproto_coverage_switch_plus_ova_nonbenign` is the deployment operating policy.
4. `actionable_coverage` is the deployment-facing success metric.
5. hardest cross protocols remain a limitation.

## 10. Reviewer Attack Surface And Prepared Answers

### Attack 1: Why not just loosen the threshold?

Answer:

1. use `Figure 4`
2. show that `0.14` buys little extra actionable coverage
3. show the visible drop in cross-scenario safe unknown handling
4. explain why `0.12` is the stable compromise

### Attack 2: Why is the mainline not the highest-coverage detector?

Answer:

1. because the paper's objective is safe deployment
2. the aggressive line belongs to deployment policy
3. the backbone and the policy should not be conflated

### Attack 3: Final defer is still high. Why is this useful?

Answer:

1. acknowledge the limitation
2. show that actionable coverage still rises materially
3. show that unknown routing remains safe
4. show that review benign rate remains low
5. frame the contribution as honest workload shaping

### Attack 4: Why is this a WASA paper?

Answer:

1. edge and networked AI threat detection
2. deployment-time workflow under uncertainty
3. queue and throughput evidence
4. systems framing rather than detector-only framing

### Attack 5: Is this cross-dataset validation?

Answer:

1. no, not in the strong sense
2. it is benchmark-scoped across two `Ca-Bench` scenarios and scenario-shift protocols
3. state this honestly in the discussion section

## 11. Suggested Writing Order From Now

Write the paper in this order:

1. Results section
2. Figure captions
3. Experimental setup
4. Method
5. Introduction
6. Conclusion
7. Abstract
8. Related work

Reason:

1. the results and figures lock the factual story
2. the introduction becomes much easier once the real claim is frozen
3. the abstract should be written last so that it matches the final wording

## 12. Figure Caption Strategy

Each caption should do three things:

1. describe what the figure shows
2. state the take-home message
3. make the backbone/policy distinction explicit where relevant

Examples:

### Figure 1

> Overview of the canonical OpenFedBot deployment stack. A conservative automatic backbone is separated from the deployment operating policy so that first-stage automatic safety and deployment-time workflow value can be analyzed independently.

### Figure 2

> Evidence for using `cpd_shift_multiproto_consensus_plus` as the paper's safe automatic backbone. The figure separates the conservative automatic operating plane from paired comparisons against the older shift-consensus line and the more aggressive coverage-switch operating line.

### Figure 3

> Deployment value arises from workload shaping rather than from claiming that automation is solved. The figure combines actionable coverage, queue cost, and hardest-protocol behavior in a single deployment-facing view.

### Figure 4

> Threshold selection for the coverage-switch policy. The canonical threshold `0.12` remains preferred because larger threshold values provide only marginal coverage gain while causing a clear reduction in cross-scenario safe unknown handling.

## 13. Direct Writing Checklist

Before calling the manuscript draft complete, verify:

1. every headline number traces back to `digest_cov12/reinforced_digest_20260408T040419Z`
2. the paper never calls the benchmark collection `multiple datasets`
3. the backbone and policy are never conflated
4. `actionable_coverage` is clearly distinguished from `coverage`
5. the hardest cross protocols are discussed explicitly
6. the threshold decision is justified with the sweep
7. stress-digest deployment numbers are not used in the main paper
8. the limitations section states the scope honestly

## 14. Minimal Deliverables For The Next Writing Step

The next concrete writing milestone should be:

1. fill in the results section using the numbers in this document
2. attach the four main figures
3. create the four main tables from the canonical digest
4. then write the introduction against the now-fixed story

If writing stalls, come back to this rule:

Write the paper as a deployment-safety paper. Do not drift back to a detector leaderboard paper.
