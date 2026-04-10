SHELL := /bin/bash

PYTHON ?= python
GRAPH_ROOT ?= assets/public_cabench_v1
RESULTS_ROOT ?= results
CONFIG ?= configs/open_world_mimic_reinforced_smoke.json
RUN_DIR ?=
DIGEST_DIR ?=
COV10_DIGEST_DIR ?=
COV14_DIGEST_DIR ?=
AUTHORITATIVE_MANIFEST ?=
CABENCH_ROOT ?=

SMOKE_CONFIG ?= configs/open_world_mimic_reinforced_smoke.json
MAINLINE_CONFIG ?= configs/open_world_full_suite_multiproto_coverageswitch_clean_seed10.json
COV10_CONFIG ?= configs/open_world_full_suite_multiproto_coverageswitch_clean_seed10_cov10.json
COV14_CONFIG ?= configs/open_world_full_suite_multiproto_coverageswitch_clean_seed10_cov14.json

CANONICAL_RUN ?= results/open_world_full_suite_multiproto_coverageswitch_clean_seed10_20260408T023210Z
CANONICAL_DIGEST ?= results/digest_cov12/reinforced_digest_20260408T040419Z
CANONICAL_COV10_DIGEST ?= results/digest_cov10/reinforced_digest_20260408T040323Z
CANONICAL_COV14_DIGEST ?= results/digest_cov14/reinforced_digest_20260408T040323Z

.PHONY: help prepare-public-assets check-env validate validate-smoke validate-mainline validate-cov10 validate-cov14 run smoke mainline cov10 cov14 digest digest-canonical bundle bundle-canonical figures figures-canonical clean-pyc

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z0-9_.-]+:.*## / {printf "%-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

prepare-public-assets: ## Build repo-local graph assets from CABENCH_ROOT=<path-to-Ca-Bench>
	@test -n "$(CABENCH_ROOT)" || (echo "CABENCH_ROOT is required" >&2; exit 1)
	$(PYTHON) scripts/prepare_public_graphs.py \
		--cabench-root $(CABENCH_ROOT) \
		--output-root $(GRAPH_ROOT) \
		--python $(PYTHON)

check-env: ## Verify the Python environment against validated versions
	$(PYTHON) scripts/check_env.py --strict

validate: ## Validate the graph schema for CONFIG=<config>
	$(PYTHON) scripts/validate_graph_schema.py --config $(CONFIG) --graph-root $(GRAPH_ROOT)

validate-smoke: CONFIG = $(SMOKE_CONFIG)
validate-smoke: validate ## Validate the reviewer smoke config against repo-local graph assets

validate-mainline: CONFIG = $(MAINLINE_CONFIG)
validate-mainline: validate ## Validate the reviewer mainline config against repo-local graph assets

validate-cov10: CONFIG = $(COV10_CONFIG)
validate-cov10: validate ## Validate the coverage-0.10 config against repo-local graph assets

validate-cov14: CONFIG = $(COV14_CONFIG)
validate-cov14: validate ## Validate the coverage-0.14 config against repo-local graph assets

run: ## Run an experiment with CONFIG=<config>
	$(PYTHON) scripts/run_experiment.py --config $(CONFIG) --graph-root $(GRAPH_ROOT) --output-root $(RESULTS_ROOT)

smoke: CONFIG = $(SMOKE_CONFIG)
smoke: run ## Run the maintained smoke experiment with repo-local inputs and outputs

mainline: CONFIG = $(MAINLINE_CONFIG)
mainline: run ## Run the canonical paper-facing mainline with repo-local inputs and outputs

cov10: CONFIG = $(COV10_CONFIG)
cov10: run ## Run the coverage-0.10 ablation with repo-local inputs and outputs

cov14: CONFIG = $(COV14_CONFIG)
cov14: run ## Run the coverage-0.14 ablation with repo-local inputs and outputs

digest: ## Rebuild a digest from RUN_DIR=<results/run_dir>
	@test -n "$(RUN_DIR)" || (echo "RUN_DIR is required" >&2; exit 1)
	$(PYTHON) scripts/build_reinforced_digest.py \
		--run-dir $(RUN_DIR) \
		--output-root $(RESULTS_ROOT) \
		--reference-method cpd_shift_multiproto_consensus_plus \
		--paper-main-method cpd_shift_multiproto_consensus_plus \
		--paper-baselines cpd_shift_consensus_plus cpd_shift_multiproto_coverage_switch_plus ova_gate msp energy \
		--paper-main-policy triage_shift_multiproto_coverage_switch_plus_ova_nonbenign \
		--paper-appendix-policies triage_shift_multiproto_consensus_plus_ova_nonbenign triage_shift_multiproto_consensus_gate_plus_ova_nonbenign \
		--comparators cpd_shift_consensus_plus cpd_shift_multiproto_coverage_switch_plus cpd_shift_multiproto_consensus_gate_plus \
		--bank-selection adaptive \
		--bank-selection-metric cpd_val_coverage \
		--bank-selection-tie-break-metric cpd_val_risk

digest-canonical: ## Rebuild the canonical digest from the frozen workspace run
	$(PYTHON) scripts/build_reinforced_digest.py \
		--run-dir $(CANONICAL_RUN) \
		--output-root $(RESULTS_ROOT)/digest_cov12 \
		--reference-method cpd_shift_multiproto_consensus_plus \
		--paper-main-method cpd_shift_multiproto_consensus_plus \
		--paper-baselines cpd_shift_consensus_plus cpd_shift_multiproto_coverage_switch_plus ova_gate msp energy \
		--paper-main-policy triage_shift_multiproto_coverage_switch_plus_ova_nonbenign \
		--paper-appendix-policies triage_shift_multiproto_consensus_plus_ova_nonbenign triage_shift_multiproto_consensus_gate_plus_ova_nonbenign \
		--comparators cpd_shift_consensus_plus cpd_shift_multiproto_coverage_switch_plus cpd_shift_multiproto_consensus_gate_plus \
		--bank-selection adaptive \
		--bank-selection-metric cpd_val_coverage \
		--bank-selection-tie-break-metric cpd_val_risk

bundle: ## Build a submission bundle from DIGEST_DIR=<digest_dir> or AUTHORITATIVE_MANIFEST=<manifest>
	@manifest="$(AUTHORITATIVE_MANIFEST)"; \
	if [ -z "$$manifest" ] && [ -n "$(DIGEST_DIR)" ]; then \
		manifest="$(DIGEST_DIR)/paper_authoritative_manifest.json"; \
	fi; \
	[ -n "$$manifest" ] || (echo "Set DIGEST_DIR or AUTHORITATIVE_MANIFEST" >&2; exit 1); \
	$(PYTHON) scripts/build_submission_bundle.py \
		--authoritative-manifest "$$manifest" \
		--output-root $(RESULTS_ROOT) \
		--paper-draft docs/wasa_paper_draft_20260409.md \
		--playbook docs/repro_submission_playbook_20260409.md \
		--submission-packet docs/wasa_submission_packet_20260409.md \
		--experiment-note docs/wasa_submission_convergence_20260408.md

bundle-canonical: ## Build the paper-facing submission bundle from the frozen canonical digest
	$(PYTHON) scripts/build_submission_bundle.py \
		--authoritative-manifest $(CANONICAL_DIGEST)/paper_authoritative_manifest.json \
		--output-root $(RESULTS_ROOT) \
		--paper-draft docs/wasa_paper_draft_20260409.md \
		--playbook docs/repro_submission_playbook_20260409.md \
		--submission-packet docs/wasa_submission_packet_20260409.md \
		--experiment-note docs/wasa_submission_convergence_20260408.md

figures: ## Build paper-facing figures from DIGEST_DIR, COV10_DIGEST_DIR, and COV14_DIGEST_DIR
	@test -n "$(DIGEST_DIR)" || (echo "DIGEST_DIR is required" >&2; exit 1)
	@test -n "$(COV10_DIGEST_DIR)" || (echo "COV10_DIGEST_DIR is required" >&2; exit 1)
	@test -n "$(COV14_DIGEST_DIR)" || (echo "COV14_DIGEST_DIR is required" >&2; exit 1)
	$(PYTHON) scripts/build_wasa_main_figures.py \
		--digest-dir $(DIGEST_DIR) \
		--cov10-digest-dir $(COV10_DIGEST_DIR) \
		--cov14-digest-dir $(COV14_DIGEST_DIR) \
		--output-root $(RESULTS_ROOT)

figures-canonical: ## Build paper-facing figures from the frozen canonical digests
	$(PYTHON) scripts/build_wasa_main_figures.py \
		--digest-dir $(CANONICAL_DIGEST) \
		--cov10-digest-dir $(CANONICAL_COV10_DIGEST) \
		--cov14-digest-dir $(CANONICAL_COV14_DIGEST) \
		--output-root $(RESULTS_ROOT)

clean-pyc: ## Remove Python bytecode caches from source directories
	find openfedbot scripts -type d -name __pycache__ -prune -exec rm -rf {} +
	find openfedbot scripts -type f -name "*.pyc" -delete
