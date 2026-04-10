# OpenFedBot Graph Schema Contract v1

This document defines the local graph contract used by `OpenFedBot`.

The purpose of the contract is to make `OpenFedBot` depend on a stable local schema instead of a specific upstream repository layout. `Ca-Bench` is one valid external data source, but it is not the schema owner.

## Required Graph Fields

The serialized graph object must expose:

1. `x_norm`
   A rank-2 `torch.Tensor` with shape `[num_nodes, num_features]`.
2. `edge_index`
   A rank-2 `torch.Tensor` with shape `[2, num_edges]`.
3. `window_idx`
   A rank-1 `torch.Tensor` with length `num_nodes`.
4. `ip_idx`
   A rank-1 `torch.Tensor` with length `num_nodes`.
5. `source_ips`
   A non-empty sequence whose order defines the mapping from `ip_idx >= 0` to source IP metadata.

## Optional Graph Fields

The following fields are optional but supported:

1. `temporal_train_mask`
2. `val_mask`
3. `test_mask`
4. `graph_schema_version`
5. `manifest_file`
6. `dataset_name`
7. `dataset_variant`
8. `dataset_source`

If the train/val/test masks are absent, `OpenFedBot` derives a temporal split from `window_idx`.

## Manifest Contract

Every graph must have a manifest either:

1. passed explicitly through the config as `manifest_path`, or
2. stored in `graph.manifest_file`.

The manifest must include:

1. `roles`
   A mapping from source IP string to role string.

The current loader interprets role strings as:

1. `benign_user` -> `benign`
2. `bot:<family>` -> `<family>`
3. `target` -> `target`

## Config Contract

The preferred config format is:

```json
{
  "graph_root": "/path/to/graph_assets",
  "scenario_graphs": {
    "scenario_e": {
      "graph_path": "graphs/cabench_scenario_e_three_tier_high2_public_graph.pt",
      "manifest_path": "meta/cabench_scenario_e_three_tier_high2_public_manifest.json"
    },
    "scenario_h": {
      "graph_path": "graphs/cabench_scenario_h_mimic_heavy_overlap_public_graph.pt",
      "manifest_path": "meta/cabench_scenario_h_mimic_heavy_overlap_public_manifest.json"
    }
  }
}
```

Legacy compatibility is still supported:

```json
{
  "hitrust_root": "/path/to/HiTrust-FedBot",
  "scenario_graphs": {
    "scenario_e": "data_hitrust/public_benchmarks/cabench_v1/graphs/cabench_scenario_e_three_tier_high2_public_graph.pt"
  }
}
```

The legacy form is tolerated for transition purposes only.

## Validation

Validate a graph directly:

```bash
python scripts/validate_graph_schema.py \
  --graph /path/to/graph.pt \
  --manifest /path/to/manifest.json
```

Validate all graphs referenced by a config:

```bash
python scripts/validate_graph_schema.py \
  --config configs/open_world_full_suite_reinforced_seed10.json
```
