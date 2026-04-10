# Next Experiment Roadmap

Date: 2026-04-07

## Current Local Baseline

Use these as the new internal baselines:

1. auto gate: `cpd_consensus_plus`
2. main triage: `triage_consensus_plus_ova`
3. low-review mode: `triage_consensus_plus_prototype_nonbenign`

Authoritative digest for this stage:

- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T025914Z`

## External Code And Paper Scan

### 1. Shift-aware selective scoring

Paper:

- Selective Classification Under Distribution Shifts, TMLR 2024
  - https://arxiv.org/abs/2405.05160
  - https://github.com/sun-umn/sc_with_distshift

What matters:

- the paper explicitly studies selective classification under distribution shift
- it proposes margin-based confidence scores for shifted deployment
- the public code is lightweight and centered on score collection and RC-curve analysis

Why it matters for OpenFedBot:

- your main remaining weakness is cross-scenario shift, not in-domain uncertainty
- the next selector should be shift-aware, not just more conservative

### 2. Confidence minimization on uncertainty data

Paper:

- Conservative Prediction via Data-Driven Confidence Minimization, TMLR 2024
  - https://openreview.net/pdf/a42685736595b24a9d8b27ff9b7d394ac37a54af.pdf

What matters:

- DCM minimizes confidence on an unlabeled uncertainty mixture
- the paper explicitly shows benefit for both selective classification and OOD detection
- the paper also argues that if uncertainty data resembles test unknowns, strong gains follow

Why it matters for OpenFedBot:

- you already have realistic unlabeled target-side structure
- current training is source-only supervised in `openfedbot/federated.py`
- this is the cleanest training-time hardening direction

### 3. Graph energy OOD regularization and propagation

Paper/code:

- GNNSafe, ICLR 2023
  - https://github.com/qitianwu/GraphOOD-GNNSafe

What matters from the official code:

- the repo exposes both `--use_reg` and `--use_prop`
- the README distinguishes propagation-only and propagation-plus-regularization variants

Why it matters for OpenFedBot:

- your current graph-aware uncertainty only uses prototype geometry plus post-hoc OVA agreement
- you do not yet use graph energy propagation or energy regularization during training

### 4. Graph conformal uncertainty with neighborhood aggregation

Paper/code:

- Conformalized GNN, NeurIPS 2023
  - https://github.com/snap-stanford/conformalized-gnn
- SNAPS, NeurIPS 2024
  - https://arxiv.org/abs/2405.14303
  - https://github.com/janqsong/SNAPS

What matters:

- CF-GNN brings conformal prediction to graph models
- SNAPS improves efficiency by aggregating nonconformity scores using feature similarity and structural neighborhood
- this is directly relevant because your auto gate still depends heavily on a strict singleton-style decision

Why it matters for OpenFedBot:

- the remaining loss is not just raw misroute; it is that the auto gate is too sparse in cross-scenario cases
- graph-aware set refinement is the most principled post-hoc way to increase safe singleton acceptance

### 5. Learning-to-defer benchmark methods

Paper/code:

- Human-AI Deferral benchmark
  - https://github.com/clinicalml/human_ai_deferral

What matters from the official benchmark:

- it implements `CompareConfidence`, `OvASurrogate`, `LCESurrogate`, `Diff-Triage`, `MixOfExps`, and `RealizableSurrogate`
- the repo is specifically about learning a classifier plus rejector that decides when to defer

Why it matters for OpenFedBot:

- your current triage is still rule-based
- review benign load remains high in the main pipeline even after `cpd_consensus_plus`
- a learned rejector is the most direct route to lower review burden without collapsing actionable coverage

### 6. Self-supervised graph intrusion detection

Paper/code:

- GraphIDS, NeurIPS 2025
  - https://arxiv.org/abs/2509.16625
  - https://github.com/lorenzo9uerra/GraphIDS

What matters:

- GraphIDS learns graph representations of normal traffic patterns through self-supervision
- the public code combines inductive GraphSAGE-style local embeddings and reconstruction

Why it matters for OpenFedBot:

- your hardest cross-scenario failures suggest source-supervised embeddings are not sufficiently invariant
- self-supervised normal-pattern pretraining is a plausible representation fix for the `h_to_e_*` cases

## Recommended Next Experiments

Order matters. Do these in sequence.

### P0. Shift-Aware Selector

Goal:

- improve cross-scenario automatic coverage and selective risk without materially harming unknown routing

Core idea:

- keep `cpd_consensus_plus` as the safety floor
- add a shift-aware selector score inspired by shift-aware selective classification
- estimate target-side shift from unlabeled target support or target flow embeddings
- reweight calibration or threshold selection by similarity to the target-side embedding distribution

Implementation hook:

- `openfedbot/calibration.py`
- `scripts/run_experiment.py`

Minimal design:

1. collect source validation embedding statistics
2. collect target support embedding statistics
3. build a shift score or density-ratio proxy
4. use that proxy to weight the acceptance score or the threshold selection

Candidate score:

- `min(z_conf, z_proto, z_ova, z_shift)`

where `z_shift` is higher for target-like points and lower for points far from target support density.

Success criteria:

- cross auto coverage `>= 0.18`
- cross selective risk `<= 0.32`
- cross unknown misroute `<= 0.045`

### P1. Graph-Conformal Gate

Goal:

- increase singleton-safe acceptance on cross scenarios using topology and embedding similarity

Core idea:

- replace the current rigid APS-singleton step with a graph-aware conformal acceptance rule
- borrow from SNAPS: aggregate nonconformity scores using feature similarity and one-hop neighborhood

Implementation hook:

- `openfedbot/calibration.py`
- optionally add helper code under `openfedbot/metrics.py` or a new module

Minimal design:

1. build k-NN neighbors in embedding space for calibration/test nodes
2. combine local nonconformity with neighbor nonconformity
3. test graph-aware singleton acceptance versus vanilla APS singleton

Success criteria:

- beat `cpd_consensus_plus` on `e_to_h_slowburn` and `e_to_h_mimic`
- no more than `+0.005` cross unknown misroute increase overall

### P2. DCM-Style Training Hardening

Goal:

- attack the real remaining bottleneck: hardest cross protocols

Core idea:

- add a confidence-minimization or energy-regularization term on unlabeled target-side uncertainty data
- uncertainty data should be a realistic mixture, not synthetic noise

Local candidate uncertainty sets:

1. target support nodes
2. target flow nodes excluded from supervised source training
3. optionally auto-rejected target nodes from a warm-start model

Implementation hook:

- `openfedbot/federated.py`
- possibly `openfedbot/model.py`
- `scripts/run_experiment.py`

Minimal design:

1. train current supervised model
2. add an auxiliary loss on unlabeled target-side nodes
3. minimize max-softmax or energy confidence on that set
4. compare against source-only training

Success criteria:

- `h_to_e_slowburn` selective risk `< 0.75`
- `h_to_e_burst` selective risk `< 0.72`
- overall cross unknown misroute not worse than `0.045`

### P3. Learned Deferral Policy

Goal:

- lower review benign load without paying the full actionable-coverage penalty of nonbenign-only review

Core idea:

- train a separate rejector on top of auto and review features
- approximate the learning-to-defer benchmark inside OpenFedBot

Features to use:

1. auto confidence margin
2. prototype margin
3. OVA margin
4. agreement flags
5. predicted class
6. graph degree or local density proxy
7. review-model confidence

Training target:

- whether review improves utility over auto for the sample

Implementation hook:

- `openfedbot/calibration.py`
- a new small module for rejector fitting
- `scripts/run_experiment.py`

Benchmark against:

1. `triage_consensus_plus_ova`
2. `triage_consensus_plus_prototype_nonbenign`
3. compare-confidence style routing

Success criteria:

- cross actionable coverage `>= 0.62`
- cross review benign rate `<= 0.25`
- cross safe unknown handling `>= 0.96`

### P4. Self-Supervised Pretraining

Goal:

- strengthen representation quality before deferral and conformal gating

Core idea:

- pretrain a normal-pattern encoder on benign/support traffic before supervised federated fine-tuning

Implementation hook:

- `openfedbot/model.py`
- `openfedbot/federated.py`

This is higher effort and should only start after P0-P3.

## Immediate Execution Order

Do not parallelize blindly. The lowest-risk path is:

1. P0 shift-aware selector on targeted hardest-cross subset
2. P1 graph-conformal gate on the same targeted subset
3. keep whichever of P0 or P1 wins as the new post-hoc gate
4. P2 DCM-style training hardening on targeted subset
5. if review burden still blocks the paper story, run P3 learned deferral
6. only then consider P4 self-supervised pretraining

## Concrete Targeted Configs To Add Next

Add these next, rather than starting from the full reinforced suite:

1. `configs/open_world_shiftaware_targeted.json`
2. `configs/open_world_graphconformal_targeted.json`
3. `configs/open_world_dcm_targeted.json`
4. `configs/open_world_learned_deferral_targeted.json`

Each should use:

- hardest cross protocols first
- clean first, then stress
- three seeds first, then ten seeds after a win

## Paper Positioning Impact

If P0-P3 work as expected, the paper story becomes:

1. `cpd_consensus_plus` is no longer just conservative; it is shift-aware
2. review is no longer a blunt second stage; it is selectively invoked
3. the system has two operating modes:
   - high-action mode
   - low-review mode
4. the hardest-cross limitation remains, but is now a bounded frontier rather than a collapse point
