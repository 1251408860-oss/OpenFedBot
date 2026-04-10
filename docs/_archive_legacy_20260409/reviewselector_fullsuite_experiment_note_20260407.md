# Review-Selector Full-Suite Note

Date: 2026-04-07

## Recommended Paper Mainline

Use:

1. auto gate: `cpd_consensus_plus`
2. calibration policy: adaptive bank selection
3. main deployment policy: `triage_consensus_plus_prototype_or_ova_selective`
4. appendix low-review policy: `triage_consensus_plus_prototype_nonbenign`
5. appendix intermediate policy: `triage_consensus_plus_ova_selective`
6. appendix targeted adaptation: `hybrid pseudo`

Primary run:

- `/home/user/workspace/OpenFedBot/results/open_world_full_suite_reviewselector_seed10_20260407T060213Z`

Authoritative digest:

- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z`

## Adaptive Selection Rule

The digest now chooses one calibration bank per `(protocol, seed)` from `calibration_metrics.csv`:

1. maximize `cpd_val_coverage`
2. tie-break with minimum `cpd_val_risk`

Observed selection counts in the authoritative digest:

1. overall: `medium 45`, `large 40`, `small 35`
2. cross only: `medium 26`, `large 18`, `small 16`

So fixed `large` should no longer be treated as the paper mainline.

## Main Full-Suite Results

From the authoritative digest using adaptive bank selection:

- cross `cpd_consensus_plus`
  - coverage `0.1485`
  - selective_risk `0.2326`
  - unknown_misroute_rate `0.0208`
  - accepted_known_macro_f1 `0.6175`
  - alerts_per_10k_benign `6.09`
- same `cpd_consensus_plus`
  - coverage `0.2091`
  - selective_risk `0.0393`
  - unknown_misroute_rate `0.0231`
  - accepted_known_macro_f1 `0.9585`
  - alerts_per_10k_benign `4.14`

- cross `triage_consensus_plus_prototype_or_ova_selective`
  - actionable_coverage `0.6781`
  - auto_coverage `0.1485`
  - review_benign_rate `0.1918`
  - review_unknown_capture_rate `0.7173`
  - safe_unknown_handling_rate `0.9792`
  - final_defer_rate `0.3219`
- same `triage_consensus_plus_prototype_or_ova_selective`
  - actionable_coverage `0.7665`
  - auto_coverage `0.2091`
  - review_benign_rate `0.2037`
  - review_unknown_capture_rate `0.7785`
  - safe_unknown_handling_rate `0.9769`
  - final_defer_rate `0.2335`

## Why Adaptive Replaces Fixed `large`

Compared with the fixed-`large` digest built from the same run:

1. cross auto coverage improved from `0.1402` to `0.1485`
2. cross auto selective risk improved from `0.2765` to `0.2326`
3. cross unknown misroute improved from `0.0214` to `0.0208`
4. cross accepted-known macro F1 improved from `0.6126` to `0.6175`
5. cross benign alerts improved from `6.56` to `6.09` per `10k`
6. cross triage actionable coverage improved from `0.6740` to `0.6781`
7. cross final defer improved from `0.3260` to `0.3219`
8. same review benign rate improved from `0.2113` to `0.2037`

The cross review benign rate moved from `0.1879` to `0.1918`, so this is a small tradeoff, not a free win on every axis.

## Review-Policy Story

The new review stage is no longer a blunt `ova_gate`.

`review_prototype_or_ova_selective` combines:

1. `prototype_only_nonbenign` as a low-benign high-capture review path
2. `ova_gate_selective` as a benign-budgeted recovery path

Under the same adaptive digest:

1. old `triage_consensus_plus_ova` cross `review_benign_rate = 0.4323`
2. old `triage_consensus_plus_ova` cross `actionable_coverage = 0.6316`
3. new main policy cross `review_benign_rate = 0.1918`
4. new main policy cross `actionable_coverage = 0.6781`

This is the strongest deployment-facing result in the current full suite.

## Hardest-Cross Status

The hardest automatic cross protocols improved materially under adaptive bank selection, but are still not fully solved:

1. `h_to_e_slowburn`: coverage `0.0564 -> 0.0860`, selective risk `0.6227 -> 0.5040`
2. `h_to_e_burst`: coverage `0.0894 -> 0.1236`, selective risk `0.6210 -> 0.4938`

So the correct paper statement is:

1. the review-burden limitation is materially reduced
2. the hardest-cross automatic-gating limitation remains a bounded frontier, not a solved problem

## Comparison Nuance To Keep Honest

Do not overclaim against `cpd_consensus`.

In the adaptive paired summary:

1. `coverage` improves with `p = 0.00048828125`
2. `selective_risk` improves with `p = 0.03857421875`
3. `accepted_known_macro_f1` improves with `p = 0.00634765625`
4. `unknown_misroute_rate` is not a clean headline win, `p = 0.0625`

So `cpd_consensus` should stay as a comparison or ablation, not the main headline opponent.

## Practical Paper Positioning

The stable systems-paper claim is now:

1. OpenFedBot keeps a conservative automatic gate for safety.
2. It adds a selective review layer that materially improves actionable coverage.
3. adaptive bank selection improves the cross operating point and hardest-cross frontier over fixed `large`.
4. the selective review layer does this without the previous benign-review explosion.
5. the remaining limitation is concentrated in hardest cross-scenario auto acceptance.
