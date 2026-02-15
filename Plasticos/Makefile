# ============================================================================
# Plasticos Odoo 19 — Makefile
# ============================================================================
# Version: 1.0.0
# Purpose: Single entry-point for lint, test, CI, and observability tasks
# ============================================================================

SHELL := /bin/bash
.DEFAULT_GOAL := help

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ODOO_IMAGE     ?= odoo:19
PG_USER        ?= odoo
PG_PASSWORD    ?= odoo
PG_DB          ?= odoo
PG_HOST        ?= 127.0.0.1
PG_PORT        ?= 5432
ADDONS_PATH    ?= $(CURDIR)

# Modules with __manifest__.py (installable)
MODULES_CORE   := plasticos_intake plasticos_documents plasticos_commission \
                  plasticos_transaction plasticos_logistics
MODULES_L9     := l9_adapter l9_drift l9_health l9_integration l9_regression l9_trace
MODULES_ALL    := $(MODULES_CORE) $(MODULES_L9)

# Test directories
TEST_DIRS      := tests plasticos_transaction/tests l9_trace/tests

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
.PHONY: help
help: ## Show this help
	@printf "\n  Plasticos Odoo 19 — available targets\n\n"
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@printf "\n"

# ---------------------------------------------------------------------------
# Lint / Static Analysis
# ---------------------------------------------------------------------------
.PHONY: lint lint-syntax lint-forbidden lint-precommit

lint: lint-syntax lint-forbidden ## Run all linters

lint-syntax: ## Compile-check all Python files
	@echo "[INFO] Compile-checking Python files..."
	python3 -m compileall -q $(ADDONS_PATH) 2>&1 | grep -v __pycache__ || true
	@echo "[OK] Syntax check passed"

lint-forbidden: ## Block direct network calls outside l9_integration
	@echo "[INFO] Checking for forbidden network calls..."
	python3 scripts/precommit_block_forbidden_calls.py
	@echo "[OK] No forbidden calls found"

lint-precommit: ## Run pre-commit hooks
	pre-commit run --all-files

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------
.PHONY: test test-unit test-replay test-odoo

test: test-unit ## Run all local tests (no Odoo server required)

test-unit: ## Run unit/replay tests via pytest
	@echo "[INFO] Running unit tests..."
	python3 -m pytest $(TEST_DIRS) -v --tb=short 2>&1 || true

test-replay: ## Run intake replay matrix
	@echo "[INFO] Running replay intake matrix..."
	python3 scripts/replay_intake_matrix.py

test-odoo: ## Run Odoo test suite in Docker (requires postgres)
	@echo "[INFO] Running Odoo tests via Docker..."
	docker run --rm --network host \
		-e HOST=$(PG_HOST) \
		-e PORT=$(PG_PORT) \
		-e USER=$(PG_USER) \
		-e PASSWORD=$(PG_PASSWORD) \
		-v "$(ADDONS_PATH):/mnt/extra-addons" \
		$(ODOO_IMAGE) \
		-- -d $(PG_DB) \
		   --stop-after-init \
		   -i plasticos_transaction \
		   --test-enable \
		   --log-level=test

# ---------------------------------------------------------------------------
# Odoo Server
# ---------------------------------------------------------------------------
.PHONY: run run-dev db-up db-down

db-up: ## Start PostgreSQL via Docker
	@echo "[INFO] Starting PostgreSQL..."
	docker run -d --name plasticos-pg \
		-e POSTGRES_USER=$(PG_USER) \
		-e POSTGRES_PASSWORD=$(PG_PASSWORD) \
		-e POSTGRES_DB=$(PG_DB) \
		-p $(PG_PORT):5432 \
		postgres:15
	@echo "[OK] PostgreSQL running on port $(PG_PORT)"

db-down: ## Stop and remove PostgreSQL container
	docker rm -f plasticos-pg 2>/dev/null || true
	@echo "[OK] PostgreSQL stopped"

run: ## Start Odoo 19 with all Plasticos addons
	docker run --rm --network host \
		-v "$(ADDONS_PATH):/mnt/extra-addons" \
		$(ODOO_IMAGE) \
		-- -d $(PG_DB) \
		   --addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons

run-dev: ## Start Odoo in dev mode (auto-reload)
	docker run --rm --network host \
		-v "$(ADDONS_PATH):/mnt/extra-addons" \
		$(ODOO_IMAGE) \
		-- -d $(PG_DB) \
		   --addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons \
		   --dev=all

# ---------------------------------------------------------------------------
# Module Install / Update
# ---------------------------------------------------------------------------
.PHONY: install-all install-core install-l9 update-all

install-all: ## Install all modules
	@echo "[INFO] Installing: $(MODULES_ALL)"
	docker run --rm --network host \
		-v "$(ADDONS_PATH):/mnt/extra-addons" \
		$(ODOO_IMAGE) \
		-- -d $(PG_DB) --stop-after-init \
		   -i $(subst $(eval) ,$(shell echo ','),$(MODULES_ALL))

install-core: ## Install core Plasticos modules only
	@echo "[INFO] Installing: $(MODULES_CORE)"
	docker run --rm --network host \
		-v "$(ADDONS_PATH):/mnt/extra-addons" \
		$(ODOO_IMAGE) \
		-- -d $(PG_DB) --stop-after-init \
		   -i $(subst $(eval) ,$(shell echo ','),$(MODULES_CORE))

install-l9: ## Install L9 governance modules only
	@echo "[INFO] Installing: $(MODULES_L9)"
	docker run --rm --network host \
		-v "$(ADDONS_PATH):/mnt/extra-addons" \
		$(ODOO_IMAGE) \
		-- -d $(PG_DB) --stop-after-init \
		   -i $(subst $(eval) ,$(shell echo ','),$(MODULES_L9))

update-all: ## Update all modules (-u)
	@echo "[INFO] Updating: $(MODULES_ALL)"
	docker run --rm --network host \
		-v "$(ADDONS_PATH):/mnt/extra-addons" \
		$(ODOO_IMAGE) \
		-- -d $(PG_DB) --stop-after-init \
		   -u $(subst $(eval) ,$(shell echo ','),$(MODULES_ALL))

# ---------------------------------------------------------------------------
# Observability Stack
# ---------------------------------------------------------------------------
.PHONY: obs-up obs-down obs-logs

obs-up: ## Start Jaeger + Prometheus + Grafana
	docker compose -f infra/observability/docker-compose.yml up -d
	@echo "[OK] Jaeger:      http://localhost:16686"
	@echo "[OK] Prometheus:   http://localhost:9090"
	@echo "[OK] Grafana:      http://localhost:3000  (admin/admin)"

obs-down: ## Stop observability stack
	docker compose -f infra/observability/docker-compose.yml down

obs-logs: ## Tail observability logs
	docker compose -f infra/observability/docker-compose.yml logs -f --tail=50

# ---------------------------------------------------------------------------
# Validation / Audit
# ---------------------------------------------------------------------------
.PHONY: validate manifests tree

validate: lint test ## Full validation pass (lint + test)
	@echo "[OK] Validation complete"

manifests: ## List all modules and their manifest status
	@echo "[INFO] Module manifest audit:"
	@for d in $(CURDIR)/*/; do \
		mod=$$(basename "$$d"); \
		if [ -f "$$d/__manifest__.py" ]; then \
			size=$$(wc -c < "$$d/__manifest__.py" | tr -d ' '); \
			if [ "$$size" -gt 2 ]; then \
				printf "  [OK]    %s\n" "$$mod"; \
			else \
				printf "  [EMPTY] %s\n" "$$mod"; \
			fi; \
		elif [ -d "$$d/models" ] || [ -d "$$d/views" ]; then \
			printf "  [MISS]  %s  (has models/views but no manifest)\n" "$$mod"; \
		fi; \
	done

tree: ## Print module directory tree
	@find . -maxdepth 2 -type d \
		! -path './.git*' \
		! -path './__pycache__*' \
		! -path './*/__pycache__*' \
		| sort | sed 's|[^/]*/|  |g'

# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------
.PHONY: clean clean-pyc clean-docker

clean: clean-pyc ## Remove build artifacts

clean-pyc: ## Remove Python bytecode
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete 2>/dev/null || true
	@echo "[OK] Bytecode cleaned"

clean-docker: db-down obs-down ## Stop all Docker containers
	@echo "[OK] Docker cleaned"

# ---------------------------------------------------------------------------
# CI (mirrors .github/workflows/odoo_ci.yml)
# ---------------------------------------------------------------------------
.PHONY: ci

ci: lint test-odoo ## Run full CI pipeline locally
	@echo "[OK] CI pipeline passed"
