# ============================================================================
# Odoo_19_ReBoot — repo-root Makefile
# ============================================================================
# Delegates to Plasticos/ for Odoo targets; provides docs and README generation.
# ============================================================================

SHELL := /bin/bash
.DEFAULT_GOAL := help

REPO_ROOT := $(CURDIR)
PLASTICOS  := $(REPO_ROOT)/Plasticos

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
.PHONY: help
help: ## Show repo-root and Plasticos targets
	@printf "\n  Odoo_19_ReBoot — repo root\n\n"
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | grep -v '^plasticos-' | \
		awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@printf "\n  Plasticos (make -C Plasticos <target>):\n"
	@$(MAKE) -s -C $(PLASTICOS) help 2>/dev/null || true
	@printf "\n"

# ---------------------------------------------------------------------------
# Docs (CODE-MAP, runbook)
# ---------------------------------------------------------------------------
.PHONY: docs code-map runbook

docs: code-map runbook ## Regenerate CODE-MAP.yaml and CURSOR-RUNBOOK.md

code-map: ## Generate docs/CODE-MAP.yaml from extract_code_facts.py
	@python3 $(REPO_ROOT)/extract_code_facts.py
	@echo "[OK] docs/CODE-MAP.yaml"

runbook: ## Generate docs/CURSOR-RUNBOOK.md from generate_runbook.py
	@python3 $(REPO_ROOT)/generate_runbook.py
	@echo "[OK] docs/CURSOR-RUNBOOK.md"

# ---------------------------------------------------------------------------
# README pipeline
# ---------------------------------------------------------------------------
.PHONY: readme readme-list readme-validate

readme: ## Generate Plasticos subsystem READMEs from config
	@python3 $(REPO_ROOT)/scripts/generate_subsystem_readmes.py --skip-time-verify
	@echo "[OK] READMEs generated"

readme-list: ## List subsystems in readme_config.yaml
	@python3 $(REPO_ROOT)/scripts/generate_subsystem_readmes.py --list

readme-validate: ## Validate README coverage
	@python3 $(REPO_ROOT)/scripts/generate_subsystem_readmes.py --validate

# ---------------------------------------------------------------------------
# Plasticos delegation
# ---------------------------------------------------------------------------
.PHONY: plasticos plasticos-help plasticos-lint plasticos-test plasticos-ci

plasticos: plasticos-help ## Run default Plasticos target (help)

plasticos-help: ## Show Plasticos Makefile help
	@$(MAKE) -C $(PLASTICOS) help

plasticos-lint: ## Lint Plasticos (syntax + forbidden calls)
	@$(MAKE) -C $(PLASTICOS) lint

plasticos-test: ## Run Plasticos tests
	@$(MAKE) -C $(PLASTICOS) test

plasticos-ci: ## Run Plasticos CI (lint + Odoo Docker tests)
	@$(MAKE) -C $(PLASTICOS) ci

# ---------------------------------------------------------------------------
# One-shot: full docs + runbook (for generate_runbook.py input)
# ---------------------------------------------------------------------------
.PHONY: refresh-docs
refresh-docs: code-map runbook ## Regenerate CODE-MAP and runbook (refreshes make help in runbook via this Makefile)
	@echo "[OK] docs refreshed"
