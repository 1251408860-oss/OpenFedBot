# Hardening Experiment Note

Date: 2026-04-07

## Goal

Address the main weaknesses of the original `cpd_consensus` / `triage_consensus_ova` stack:

1. very low automatic coverage
2. weak selective-risk story
3. high benign review burden
4. weak hardest-cross behavior

## New Candidates

### `cpd_consensus_plus`

`cpd_consensus_plus` keeps the original conservative consensus gate and adds a benign reclaim path:

- predicted benign by the main model
- predicted benign by OVA
- passes prototype and OVA margins
- passes a validation-calibrated benign reclaim threshold

This raises safe automatic acceptance mainly by reclaiming low-risk benign samples that were previously deferred.

### Triage Variants

Two triage variants are worth keeping:

1. `triage_consensus_plus_ova`
   - same review analyzer as before
   - preserves the previous actionable-coverage ceiling
   - substantially reduces benign review burden by moving safe benign traffic into auto acceptance
2. `triage_consensus_plus_prototype_nonbenign`
   - review only handles non-benign prototype-positive traffic
   - much lower review benign load
   - lower actionable coverage than the default review policy

## Full Clean-Only 10-Seed Result

Run:

- `/home/user/workspace/OpenFedBot/results/open_world_full_suite_hardened_clean_seed10_20260407T024807Z`

Automatic gate summary:

- cross `cpd_consensus`:
  - coverage `0.0615`
  - selective_risk `0.5087`
  - unknown_misroute_rate `0.0364`
  - accepted_benign_fpr `0.00066`
- cross `cpd_consensus_plus`:
  - coverage `0.1471`
  - selective_risk `0.3577`
  - unknown_misroute_rate `0.0383`
  - accepted_benign_fpr `0.00066`
- same `cpd_consensus`:
  - coverage `0.1003`
  - selective_risk `0.1001`
  - unknown_misroute_rate `0.0358`
  - accepted_benign_fpr `0.00062`
- same `cpd_consensus_plus`:
  - coverage `0.2175`
  - selective_risk `0.0547`
  - unknown_misroute_rate `0.0422`
  - accepted_benign_fpr `0.00062`

Triage summary:

- cross `triage_consensus_ova`:
  - actionable_coverage `0.6385`
  - final_defer_rate `0.3615`
  - safe_unknown_handling_rate `0.9636`
  - review_benign_rate `0.7049`
- cross `triage_consensus_plus_ova`:
  - actionable_coverage `0.6385`
  - final_defer_rate `0.3615`
  - safe_unknown_handling_rate `0.9617`
  - review_benign_rate `0.4497`
- cross `triage_consensus_plus_prototype_nonbenign`:
  - actionable_coverage `0.5779`
  - final_defer_rate `0.4221`
  - safe_unknown_handling_rate `0.9617`
  - review_benign_rate `0.0160`
- same `triage_consensus_ova`:
  - actionable_coverage `0.7186`
  - final_defer_rate `0.2814`
  - safe_unknown_handling_rate `0.9642`
  - review_benign_rate `0.7553`
- same `triage_consensus_plus_ova`:
  - actionable_coverage `0.7186`
  - final_defer_rate `0.2814`
  - safe_unknown_handling_rate `0.9578`
  - review_benign_rate `0.4216`
- same `triage_consensus_plus_prototype_nonbenign`:
  - actionable_coverage `0.6518`
  - final_defer_rate `0.3482`
  - safe_unknown_handling_rate `0.9578`
  - review_benign_rate `0.0102`

## Hardest-Cross Takeaway

`cpd_consensus_plus` does not solve the hardest cross protocols, but it consistently improves them over `cpd_consensus`:

- `e_to_h_slowburn`: coverage `0.0464 -> 0.1402`, selective_risk `0.4917 -> 0.2439`
- `e_to_h_mimic`: coverage `0.0658 -> 0.1935`, selective_risk `0.3544 -> 0.1509`
- `h_to_e_burst`: coverage `0.0485 -> 0.0669`, selective_risk `0.9313 -> 0.7752`
- `h_to_e_slowburn`: coverage `0.0408 -> 0.0477`, selective_risk `0.9349 -> 0.8213`

The `h_to_e_*` protocols remain the main unresolved weakness.

## Recommendation

For the paper mainline:

1. use `cpd_consensus_plus` as the default automatic gate candidate
2. keep `triage_consensus_plus_ova` as the main deployment pipeline
3. present `triage_consensus_plus_prototype_nonbenign` as the low-review operating mode

This gives a cleaner answer to reviewer attacks:

- higher safe auto coverage than the original gate
- lower selective risk than the original gate
- far lower benign review burden without losing the old actionable ceiling
- an explicit operating-mode tradeoff for institutions with strict review budgets
