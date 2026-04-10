# Adaptive Bank Full-Suite Note

Date: 2026-04-07

## Recommendation

`adaptive bank selection` should replace the fixed `large` calibration bank as the paper mainline.

Use:

1. auto gate: `cpd_consensus_plus`
2. calibration policy: adaptive bank selection
3. deployment policy: `triage_consensus_plus_prototype_or_ova_selective`
4. `hybrid pseudo`: appendix ablation only

Authoritative digest:

- `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260407T074024Z`

## Selection Rule

The selector is frozen inside `scripts/build_reinforced_digest.py` and uses only the emitted calibration-side summary file:

1. read `calibration_metrics.csv`
2. choose one bank per `(protocol, seed)`
3. maximize `cpd_val_coverage`
4. tie-break by minimum `cpd_val_risk`

This is now a local digest-time policy, not an external Ca-Bench dependency.

## Why Fixed `large` Is No Longer the Mainline

Across the 120 `(protocol, seed)` selections in the authoritative digest, the chosen bank distribution is:

1. `medium`: `45`
2. `large`: `40`
3. `small`: `35`

Cross-scenario only:

1. `medium`: `26`
2. `large`: `18`
3. `small`: `16`

So the data no longer supports treating `large` as the default best paper-facing calibration choice.

## Mainline Gains Over Fixed `large`

Compared with the fixed-`large` digest from the same run:

1. cross `cpd_consensus_plus` coverage improved from `0.1402` to `0.1485`
2. cross `cpd_consensus_plus` selective risk improved from `0.2765` to `0.2326`
3. cross `cpd_consensus_plus` unknown misroute improved from `0.0214` to `0.0208`
4. cross benign alerts improved from `6.56` to `6.09` per `10k`
5. cross `triage_consensus_plus_prototype_or_ova_selective` actionable coverage improved from `0.6740` to `0.6781`
6. cross final defer improved from `0.3260` to `0.3219`
7. same-scenario review benign rate improved from `0.2113` to `0.2037`

The cross review benign rate moved from `0.1879` to `0.1918`, so this should be written as a small acceptable tradeoff, not as a free win on every axis.

## Hardest-Cross Status

The hardest automatic cross protocols improved materially, but they are still a limitation:

1. `h_to_e_slowburn`: coverage `0.0564 -> 0.0860`, selective risk `0.6227 -> 0.5040`
2. `h_to_e_burst`: coverage `0.0894 -> 0.1236`, selective risk `0.6210 -> 0.4938`

This is enough to justify the adaptive selector as the new mainline calibration policy, but not enough to claim the hardest cross transfers are solved.

## Writing Guidance

Use the following paper wording:

1. adaptive bank selection is the recommended calibration policy
2. it improves the cross-scenario operating point and hardest-cross frontier relative to fixed `large`
3. the paper headline remains deployment safety plus actionable coverage, not raw automatic coverage
4. `cpd_consensus` stays as a comparison/ablation, not the main headline opponent
5. `hybrid pseudo` stays in the appendix because it did not produce a stable full-suite fix
