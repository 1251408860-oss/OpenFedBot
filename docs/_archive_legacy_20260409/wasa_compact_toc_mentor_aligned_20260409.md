# WASA Compact TOC (Mentor-Aligned)

Date: 2026-04-09

This document rewrites the paper directory according to the latest mentor-aligned guidance:

1. Chapter 1: no subsections
2. Chapter 2: `Related Work`, no subsections
3. Chapter 3: rewrite as a compressed core chapter with three subsections
4. Chapter 4: results chapter with four subsections
5. Chapter 5: no subsections
6. Appendix budget: about four pages

Important:

After compression, the paper should be renumbered cleanly in the final manuscript. The most reasonable final structure is six main sections plus appendix.

## Final Recommended Main TOC

1. Introduction
2. Related Work
3. Design and Methodology
4. Evaluation
5. Discussion
6. Conclusion

This is the clean renumbered version of the mentor's advice.

## Final Detailed TOC

### 1. Introduction

No subsections.

This section should do four things in a single continuous narrative:

1. define the deployment problem
2. explain why high automatic coverage is the wrong headline
3. introduce the two-layer `OpenFedBot` idea
4. list contributions at the end of the section

Recommended internal paragraph flow:

1. deployment failure under open-world scenario shift
2. why detector-only framing is not enough
3. `OpenFedBot` as safe backbone plus deployment-time triage
4. honest scope and contributions

### 2. Related Work

No subsections.

This chapter should be short and contrastive, not a survey.

It should cover three threads in one continuous narrative:

1. open-world and selective classification for unknown-aware threat detection
2. federated and graph-based bot or anomaly detection
3. human-in-the-loop triage or abstention-oriented safe deployment

The chapter should end by stating clearly that this paper differs by treating federated open-world bot detection as a deployment-time triage problem rather than a pure detector-ranking problem.

### 3. Design and Methodology

3.1 Deployment Setting and System Overview  
3.2 OpenFedBot Design  
3.3 Experimental Methodology

This chapter is the compressed technical core of the paper. It replaces the longer multi-chapter version and should carry all essential setup needed before evaluation.

What `3.1` should contain:

1. same-scenario and cross-scenario deployment
2. leave-one-family-out open-world evaluation
3. three deployment outcomes: auto accept, review, final defer
4. distinction between `coverage` and `actionable_coverage`
5. the canonical deployment stack with `Figure 1`

What `3.2` should contain:

1. federated GraphSAGE + FedAvg backbone
2. multi-prototype safe automatic backbone
3. shift-aware conservative gating
4. coverage-switch deployment operating policy
5. adaptive calibration-bank selection

What `3.3` should contain:

1. dataset wording: two `Ca-Bench` graph scenarios from an unpublished benchmark paper under submission
2. protocols: 12 leave-one-family-out protocols
3. bot families: `burst`, `slowburn`, `mimic`
4. baselines and compared operating lines
5. training configuration
6. evaluation metrics and paired sign tests
7. graph schema contract and frozen `Ca-Bench` snapshot for reproducibility

Compression rule:

1. do not create extra micro-subsections below this level
2. keep formulas and definitions minimal and targeted
3. use tables rather than long prose when settings become dense

### 4. Evaluation

4.1 Automatic Safety  
4.2 Deployment Effectiveness  
4.3 Deployment Cost and Hard Cases  
4.4 Operating Point Analysis

This four-part structure is the strongest version for the current paper.

What `4.1` should contain:

1. `Figure 2`
2. main automatic table
3. paired comparison against `cpd_shift_consensus_plus`
4. paired comparison against `cpd_shift_multiproto_coverage_switch_plus`

What `4.2` should contain:

1. deployment policy summary
2. `actionable_coverage`
3. `safe_unknown_handling_rate`
4. `review_benign_rate`

What `4.3` should contain:

1. deployment cost table
2. queue-size or throughput evidence
3. `Figure 3`
4. hardest cross-protocol discussion

What `4.4` should contain:

1. threshold sweep
2. why `0.12` remains canonical
3. `Figure 4`

This chapter should be the longest and strongest chapter in the paper.

### 5. Discussion

No subsections.

This chapter should be one compact continuous discussion section.

It should contain:

1. what the current results do support
2. what the current results do not support
3. benchmark scope and generalization boundary
4. hardest cross-protocol limitation
5. practical deployment meaning for WASA

This chapter should explicitly state:

1. the evaluation is benchmark-scoped, not broad cross-dataset validation
2. hardest cross protocols remain unsolved at the automatic stage
3. final defer remains substantial in difficult settings
4. the main contribution is safer deployment workflow, not solved automation

### 6. Conclusion

No subsections.

The conclusion should:

1. restate the deployment-safe framing
2. restate the safe backbone plus deployment policy distinction
3. restate the strongest deployment numbers briefly
4. acknowledge the hardest-protocol limitation
5. close with future work

## Why This Compressed TOC Is Better

This version is stronger than a generic compressed directory because:

1. it preserves the deployment framing early
2. it keeps `Related Work` short and self-contained
3. it keeps method and setup compact without losing reproducibility
4. it gives the results chapter enough space to carry the paper
5. it leaves room for an honest limitations discussion

## What Must Move To Appendix

Because the main paper is page-limited, the following material should go to the appendix first:

1. extended baseline families and appendix-only policies
2. stress robustness details
3. extra threshold tables and extra sweep plots
4. extra implementation and configuration detail
5. extra per-protocol breakdown tables
6. additional case studies if they are not essential to the main claim

## Recommended Appendix Plan (4 Pages Total)

Use four appendix pages with explicit page budgeting.

### Appendix A. Extended Experimental and Reproducibility Details

Recommended length: `1.0` page

Include:

1. full training hyperparameters
2. client partition details
3. graph schema contract summary
4. digest and artifact control note
5. exact config names and run manifests

Best source material:

1. `/home/user/workspace/OpenFedBot/docs/repro_submission_playbook_20260409.md`
2. `/home/user/workspace/OpenFedBot/docs/graph_schema_contract_v1.md`

### Appendix B. Extended Baselines and Policy Comparisons

Recommended length: `1.0` page

Include:

1. appendix deployment policies
2. extra auto comparators
3. policy comparison tables not central to the main story

Best source material:

1. `triage_shift_multiproto_consensus_plus_ova_nonbenign`
2. `triage_shift_multiproto_consensus_gate_plus_ova_nonbenign`
3. adaptive paired summaries not fully discussed in the main text

### Appendix C. Stress Robustness and Additional Sweeps

Recommended length: `1.0` page

Include:

1. stress digest results
2. robustness figures
3. threshold support tables beyond the main figure

Important:

Do not quote stress deployment-cost numbers in the main text. Keep them in appendix only.

### Appendix D. Additional Hardest-Protocol or Case Study Material

Recommended length: `1.0` page

Include:

1. extended hardest-protocol breakdown
2. extra per-protocol plots
3. failure-case examples
4. supplementary qualitative interpretation

## Recommended Main-Text vs Appendix Split

### Keep in Main Text

1. system overview
2. safe backbone evidence
3. deployment triage evidence
4. deployment cost
5. hardest cross protocol summary
6. threshold selection
7. core limitation statement

### Move to Appendix

1. extended baseline variants
2. extra policy comparisons
3. stress robustness details
4. extra statistical tables
5. full implementation details
6. extra failure examples

## Best Final Directory To Use

Use this exact final directory:

1. Introduction
2. Related Work
3. Design and Methodology
4. Evaluation
5. Discussion
6. Conclusion

Use this exact results split:

1. Automatic Safety
2. Deployment Effectiveness
3. Deployment Cost and Hard Cases
4. Operating Point Analysis

Use this exact appendix split:

1. Extended Experimental and Reproducibility Details
2. Extended Baselines and Policy Comparisons
3. Stress Robustness and Additional Sweeps
4. Additional Hardest-Protocol or Case Study Material

## Final Practical Recommendation

If you start writing now, write in this order:

1. Section 4 Results
2. Section 3 Method and Experimental Setup
3. Section 2 Problem Formulation and System Overview
4. Section 1 Introduction
5. Section 5 Discussion and Related Work
6. Section 6 Conclusion
7. Appendix A to D

This writing order is the safest way to keep the paper aligned with the real evidence instead of drifting back to a detector-only story.
