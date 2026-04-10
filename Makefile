SHELL := /bin/bash

PYTHON ?= python
CONFIG ?= configs/open_world_mimic_reinforced_smoke.json
CANONICAL_RUN ?= results/open_world_full_suite_multiproto_coverageswitch_clean_seed10_20260408T023210Z
AUTHORITATIVE_MANIFEST ?= results/digest_cov12/reinforced_digest_20260408T040419Z/paper_authoritative_manifest.json

.PHONY: help check-env validate validate-smoke validate-mainline run smoke mainline digest-canonical bundle figures clean-pyc

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z0-9_.-]+:.*## / {printf "%-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

check-env: ## Verify the Python environment against validated versions
	$(PYTHON) scripts/check_env.py --strict

validate: ## Validate the graph schema for CONFIG=<config>
	$(PYTHON) scripts/validate_graph_schema.py --config $(CONFIG)

validate-smoke: CONFIG = configs/open_world_mimic_reinforced_smoke.json
validate-smoke: validate ## Validate the legacy smoke config used in this workspace

validate-mainline: CONFIG = configs/open_world_full_suite_multiproto_coverageswitch_clean_seed10.json
validate-mainline: validate ## Validate the legacy canonical mainline config used in this workspace

run: ## Run an experiment with CONFIG=<config>
	$(PYTHON) scripts/run_experiment.py --config $(CONFIG)

smoke: CONFIG = configs/open_world_mimic_reinforced_smoke.json
smoke: run ## Run the maintained smoke experiment against the legacy workspace paths

mainline: CONFIG = configs/open_world_full_suite_multiproto_coverageswitch_clean_seed10.json
mainline: run ## Run the canonical paper-facing mainline against the legacy workspace paths

digest-canonical: ## Rebuild the canonical digest from CANONICAL_RUN
	$(PYTHON) scripts/build_reinforced_digest.py \
		--run-dir $(CANONICAL_RUN) \
		--reference-method cpd_shift_multiproto_consensus_plus \
		--paper-main-method cpd_shift_multiproto_consensus_plus \
		--paper-baselines cpd_shift_consensus_plus cpd_shift_multiproto_coverage_switch_plus ova_gate msp energy \
		--paper-main-policy triage_shift_multiproto_coverage_switch_plus_ova_nonbenign \
		--paper-appendix-policies triage_shift_multiproto_consensus_plus_ova_nonbenign triage_shift_multiproto_consensus_gate_plus_ova_nonbenign \
		--comparators cpd_shift_consensus_plus cpd_shift_multiproto_coverage_switch_plus cpd_shift_multiproto_consensus_gate_plus \
		--bank-selection adaptive \
		--bank-selection-metric cpd_val_coverage \
		--bank-selection-tie-break-metric cpd_val_risk

bundle: ## Build the paper-facing submission bundle from AUTHORITATIVE_MANIFEST
	$(PYTHON) scripts/build_submission_bundle.py \
		--authoritative-manifest $(AUTHORITATIVE_MANIFEST) \
		--paper-draft docs/wasa_paper_draft_20260409.md \
		--playbook docs/repro_submission_playbook_20260409.md \
		--submission-packet docs/wasa_submission_packet_20260409.md \
		--experiment-note docs/wasa_submission_convergence_20260408.md

figures: ## Build paper-facing figures from the current digest defaults
	$(PYTHON) scripts/build_wasa_main_figures.py

clean-pyc: ## Remove Python bytecode caches from source directories
	find openfedbot scripts -type d -name __pycache__ -prune -exec rm -rf {} +
	find openfedbot scripts -type f -name "*.pyc" -delete
