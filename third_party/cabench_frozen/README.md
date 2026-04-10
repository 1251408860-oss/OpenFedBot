# Frozen Ca-Bench Builder Snapshot

This directory contains a frozen local copy of the Ca-Bench graph builder components used to derive public graph artifacts.

The purpose of this copy is to remove any runtime dependency on the upstream `main` branch.

Frozen source provenance:

1. Upstream repository: `https://github.com/1251408860-oss/Ca-Bench`
2. Frozen commit: `666af74e55f03c321557b2f2f83feb4f0950dd2d`
3. Frozen files:
   - `core_experiments/build_graph_v2.py`
   - `core_experiments/internal/submission_common.py`

The file hashes are recorded in `manifest.json`.

This snapshot is vendor code. It should not be edited casually. If the builder is refreshed, update `manifest.json` and record the new upstream commit explicitly.
