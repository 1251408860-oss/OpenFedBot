# Target Adaptation Experiment Note

Date: 2026-04-07

## Scope

This note summarizes the full target-side confidence adaptation experiment that follows the earlier hardening stage.

New full run:

- `/home/user/workspace/OpenFedBot/results/open_world_full_suite_targetadapt_seed10_20260407T041404Z`

New digest:

- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T042017Z`

Reference hardening run:

- `/home/user/workspace/OpenFedBot/results/open_world_full_suite_reinforced_seed10_20260407T025211Z`

Reference hardening digest:

- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T025914Z`

## What Was Added

The new run adds target-side confidence adaptation before final evaluation:

1. build a conservative pseudo-label set on clean target flows using `cpd_consensus_plus`
2. fine-tune the model with:
   - source supervised loss
   - pseudo-label loss on accepted target nodes
   - uniform-confidence loss on uncertain target nodes
3. recompute source-side calibration and OVA after adaptation

Implementation files:

- `/home/user/workspace/OpenFedBot/openfedbot/federated.py`
- `/home/user/workspace/OpenFedBot/scripts/run_experiment.py`
- `/home/user/workspace/OpenFedBot/configs/open_world_targetadapt_targeted.json`
- `/home/user/workspace/OpenFedBot/configs/open_world_full_suite_targetadapt_seed10.json`

## Main Result

The target-adapted `cpd_consensus_plus` becomes clearly safer than the previous hardening-stage `cpd_consensus_plus`, with only a small loss in automatic coverage.

### Full clean large summary

Hardening-stage `cpd_consensus_plus`:

- cross:
  - coverage `0.1471`
  - selective_risk `0.3577`
  - unknown_misroute_rate `0.0383`
  - accepted_benign_fpr `0.00066`
  - accepted_known_macro_f1 `0.5633`
- same:
  - coverage `0.2175`
  - selective_risk `0.0547`
  - unknown_misroute_rate `0.0422`
  - accepted_benign_fpr `0.00062`
  - accepted_known_macro_f1 `0.9244`

Target-adapted `cpd_consensus_plus`:

- cross:
  - coverage `0.1402`
  - selective_risk `0.2765`
  - unknown_misroute_rate `0.0214`
  - accepted_benign_fpr `0.00066`
  - accepted_known_macro_f1 `0.6126`
- same:
  - coverage `0.2027`
  - selective_risk `0.0367`
  - unknown_misroute_rate `0.0214`
  - accepted_benign_fpr `0.00041`
  - accepted_known_macro_f1 `0.9545`

## Run-to-Run Interpretation

Comparing the same method across the two runs:

- automatic coverage decreases slightly
- selective risk improves substantially
- unknown misroute improves substantially
- accepted known macro-F1 improves
- benign false alert rate stays essentially unchanged

Mean run-to-run deltas for `cpd_consensus_plus`:

- coverage:
  - cross `-0.0069`
  - same `-0.0148`
- selective_risk:
  - cross `-0.0811`
  - same `-0.0180`
- unknown_misroute_rate:
  - cross `-0.0169`
  - same `-0.0208`
- accepted_known_macro_f1:
  - cross `+0.0493`
  - same `+0.0302`

This is a good trade for a safety-first systems paper.

## Triage Impact

Hardening-stage `triage_consensus_plus_ova`:

- cross:
  - actionable_coverage `0.6385`
  - safe_unknown_handling_rate `0.9617`
  - review_benign_rate `0.4497`
  - auto_coverage `0.1471`
- same:
  - actionable_coverage `0.7186`
  - safe_unknown_handling_rate `0.9578`
  - review_benign_rate `0.4216`
  - auto_coverage `0.2175`

Target-adapted `triage_consensus_plus_ova`:

- cross:
  - actionable_coverage `0.6344`
  - safe_unknown_handling_rate `0.9786`
  - review_benign_rate `0.4637`
  - auto_coverage `0.1402`
- same:
  - actionable_coverage `0.7166`
  - safe_unknown_handling_rate `0.9786`
  - review_benign_rate `0.4398`
  - auto_coverage `0.2027`

Interpretation:

- actionable coverage changes only slightly
- safe unknown handling improves clearly
- review benign becomes slightly worse than hardening-stage
- the main win is safety, not review efficiency

## Hardest-Cross Status

Target adaptation improves several hardest cross cases materially:

- `e_to_h_slowburn`
  - coverage `0.1402 -> 0.0983` in targeted test was slightly lower
  - but selective risk improved strongly in targeted comparison
- `h_to_e_slowburn`
  - targeted selective risk improved from `0.7260` to `0.6005`
- `h_to_e_burst`
  - targeted selective risk improved slightly relative to hardening-stage

The strongest effect is that the worst cross-protocol safety collapse is reduced.

## Recommendation

Use target adaptation as the new default paper line if your priority is the most conservative acceptance story.

Recommended main line:

1. auto gate: `cpd_consensus_plus` from the target-adapted run
2. deployment policy: `triage_consensus_plus_ova`
3. appendix low-review mode: `triage_consensus_plus_prototype_nonbenign`

Why:

- the safety metrics become noticeably stronger
- the automatic coverage loss is small relative to the safety gain
- the paper is more defensible under reviewer scrutiny

## Paper Positioning Update

After this run, the paper story should be:

1. source-supervised federated detector
2. target-side confidence-adapted calibration
3. conservative automatic gate with benign reclaim
4. review-time triage for remaining traffic

This is stronger than the previous hardening-only story because it no longer depends purely on post-hoc gating.
