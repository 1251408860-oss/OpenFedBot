# Assets

This directory is reserved for reviewer-local runtime assets that are too large to track directly in Git.

## Expected Layout

After running `make prepare-public-assets CABENCH_ROOT=/path/to/Ca-Bench`, the repository should contain:

- `public_cabench_v1/graphs/cabench_scenario_e_three_tier_high2_public_graph.pt`
- `public_cabench_v1/graphs/cabench_scenario_h_mimic_heavy_overlap_public_graph.pt`
- `public_cabench_v1/meta/cabench_scenario_e_three_tier_high2_public_manifest.json`
- `public_cabench_v1/meta/cabench_scenario_h_mimic_heavy_overlap_public_manifest.json`
- `public_cabench_v1/asset_manifest.json`

## Source Of Truth

These files are derived from the public `Ca-Bench` packet captures under:

- `mininet_testbed/real_collection/scenario_e_three_tier_high2/`
- `mininet_testbed/real_collection/scenario_h_mimic_heavy_overlap/`

They are local build artifacts and are intentionally ignored by Git.
