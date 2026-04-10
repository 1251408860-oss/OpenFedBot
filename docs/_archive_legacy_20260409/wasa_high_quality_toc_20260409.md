# High-Quality WASA Paper TOC

Date: 2026-04-09

This is the recommended high-quality table of contents for the current `OpenFedBot` paper. It is designed for a WASA-style full paper with a systems-oriented deployment narrative, not a detector-leaderboard narrative.

## Recommended Title

Deployment-Safe Open-World Federated Bot Triage for Edge and Networked AI Threat Detection

## Recommended Table of Contents

1. Introduction
2. Problem Formulation and System Overview
3. Method
4. Experimental Setup
5. Results
6. Discussion and Limitations
7. Related Work
8. Conclusion

## Detailed Section Structure

### 1. Introduction

1.1 Background: Open-World Federated Bot Detection Under Deployment Shift  
1.2 Why High Automatic Coverage Is Not the Right Deployment Goal  
1.3 OpenFedBot: Safe Backbone Plus Deployment-Time Triage  
1.4 Main Contributions

### 2. Problem Formulation and System Overview

2.1 Deployment Setting: Same-Scenario and Cross-Scenario Open-World Evaluation  
2.2 Three Deployment Outcomes: Auto Accept, Review, and Final Defer  
2.3 Target Metrics: Coverage, Actionable Coverage, Safe Unknown Handling, and Review Burden  
2.4 Canonical OpenFedBot Deployment Stack

### 3. Method

3.1 Federated Graph Learning Backbone  
3.2 Multi-Prototype Safe Automatic Backbone  
3.3 Shift-Aware Conservative Automatic Gating  
3.4 Coverage-Switch Deployment Operating Policy  
3.5 Review Path and Unknown-Safe Routing  
3.6 Adaptive Calibration-Bank Selection  
3.7 Complexity and Deployment Considerations

### 4. Experimental Setup

4.1 Dataset and Graph Assets  
4.2 Protocol Design: Leave-One-Family-Out Across Same and Cross Scenarios  
4.3 Training and Federated Configuration  
4.4 Baselines and Compared Operating Lines  
4.5 Deployment Policies and Threshold Settings  
4.6 Evaluation Metrics  
4.7 Reproducibility and Artifact Control

### 5. Results

5.1 RQ1: Is the Automatic Backbone Safe Enough to Be the Mainline?  
5.2 RQ2: Does Deployment-Time Triage Improve Actionable Coverage Without Losing Safety?  
5.3 RQ3: What Deployment Cost and Workload Tradeoff Does the System Induce?  
5.4 RQ4: What Happens on the Hardest Cross-Scenario Protocols?  
5.5 RQ5: Why Is the Canonical Threshold Set to 0.12?  
5.6 Summary of Main Findings

### 6. Discussion and Limitations

6.1 What the Current Results Do Support  
6.2 What the Current Results Do Not Support  
6.3 Benchmark Scope and Generalization Boundary  
6.4 Hardest-Protocol Failure Modes  
6.5 Practical Deployment Interpretation

### 7. Related Work

7.1 Open-World and Selective Classification for Threat Detection  
7.2 Federated and Graph-Based Bot Detection  
7.3 Human-in-the-Loop Triage and Safe AI Deployment

### 8. Conclusion

8.1 Main Takeaway  
8.2 Honest Limitation Boundary  
8.3 Future Directions

## Best Version for the Actual Paper

Use this shorter version in the final manuscript if page budget is tight:

1. Introduction
2. Problem Formulation and System Overview
3. Method
4. Experimental Setup
5. Results
6. Discussion and Limitations
7. Related Work
8. Conclusion

With the following subsection layout:

### 1. Introduction

1.1 Motivation  
1.2 Key Idea  
1.3 Contributions

### 2. Problem Formulation and System Overview

2.1 Deployment Setting  
2.2 Metrics and Outcomes  
2.3 System Overview

### 3. Method

3.1 Federated Graph Backbone  
3.2 Safe Automatic Backbone  
3.3 Deployment Operating Policy  
3.4 Adaptive Calibration Policy

### 4. Experimental Setup

4.1 Dataset and Protocols  
4.2 Baselines and Settings  
4.3 Metrics and Statistical Evaluation

### 5. Results

5.1 Safe Backbone Evidence  
5.2 Deployment Triage Evidence  
5.3 Deployment Cost and Hardest Protocols  
5.4 Threshold Selection

### 6. Discussion and Limitations

6.1 Supported Claims  
6.2 Remaining Weaknesses  
6.3 Practical Meaning for WASA

### 7. Related Work

### 8. Conclusion

## Why This TOC Is Stronger Than a Generic AI Paper TOC

This TOC is intentionally better aligned with strong systems and deployment papers because:

1. it separates `problem formulation` from `method`, which makes the deployment abstraction explicit early
2. it does not treat the paper as a pure classifier paper
3. it centers the results around concrete research questions
4. it reserves a full discussion section for scope and limitation control
5. it gives the threshold decision and hardest-protocol behavior their own explicit narrative space

## TOC Styles To Avoid

Do not use these weak directory styles:

1. `Introduction / Related Work / Method / Experiment / Conclusion` with no deployment framing
2. a detector-style outline that hides review, defer, and queue cost until late in the paper
3. a bloated method section with too many micro-subsections but a shallow results section
4. an experiment section that mixes dataset, metrics, results, and ablation into one long block

## Final Recommendation

For the current paper, the best final directory is:

1. Introduction
2. Problem Formulation and System Overview
3. Method
4. Experimental Setup
5. Results
6. Discussion and Limitations
7. Related Work
8. Conclusion

And the strongest results subsection split is:

1. Safe Backbone Evidence
2. Deployment Triage Evidence
3. Deployment Cost and Hardest Protocols
4. Threshold Selection
