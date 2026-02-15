# CURSOR-RUNBOOK.md

**For:** Cursor IDE / AI Pair Programming + developers running L9  
**Audience:** Cursor AI Assistant, developers, ops  
**Authority:** L (CTO), Igor (Boss)  
**Generated:** 2026-02-15 23:13 UTC by `scripts/generate_runbook.py`  
**Status:** READY FOR PHASE 2 IMPLEMENTATION

---

## PART I — OPERATIONS (RUN THE STACK)

### Make targets (from `make help`)

```bash
    Odoo_19_ReBoot — repo root
    
      help                    Show repo-root and Plasticos targets
      docs                    Regenerate CODE-MAP.yaml and CURSOR-RUNBOOK.md
      code-map                Generate docs/CODE-MAP.yaml from extract_code_facts.py
      runbook                 Generate docs/CURSOR-RUNBOOK.md from generate_runbook.py
      readme                  Generate Plasticos subsystem READMEs from config
      readme-list             List subsystems in readme_config.yaml
      readme-validate         Validate README coverage
      plasticos               Run default Plasticos target (help)
      refresh-docs            Regenerate CODE-MAP and runbook (refreshes make help in runbook via this Makefile)
    
      Plasticos (make -C Plasticos <target>):
    
      Plasticos Odoo 19 — available targets
    
      help                    Show this help
      lint                    Run all linters
      lint-syntax             Compile-check all Python files
      lint-forbidden          Block direct network calls outside l9_integration
      lint-precommit          Run pre-commit hooks
      test                    Run all local tests (no Odoo server required)
      test-unit               Run unit/replay tests via pytest
      test-replay             Run intake replay matrix
      test-odoo               Run Odoo test suite in Docker (requires postgres)
      db-up                   Start PostgreSQL via Docker
      db-down                 Stop and remove PostgreSQL container
      run                     Start Odoo 19 with all Plasticos addons
      run-dev                 Start Odoo in dev mode (auto-reload)
      install-all             Install all modules
      install-core            Install core Plasticos modules only
      update-all              Update all modules (-u)
      obs-up                  Start Jaeger + Prometheus + Grafana
      obs-down                Stop observability stack
      obs-logs                Tail observability logs
      validate                Full validation pass (lint + test)
      manifests               List all modules and their manifest status
      tree                    Print module directory tree
      clean                   Remove build artifacts
      clean-pyc               Remove Python bytecode
      clean-docker            Stop all Docker containers
      ci                      Run full CI pipeline locally
```

### Required environment variables (names)

- `DATABASE_URL`
- `L9_EXECUTOR_API_KEY`

### All env vars referenced in repo (from repo-index)

- `DATABASE_URL`
- `L9_EXECUTOR_API_KEY`

### Common failure modes + fixes

- **API requests return `Executor key not configured` or `Unauthorized`.**
  - Fix: set `L9_EXECUTOR_API_KEY` and pass `Authorization: Bearer $L9_EXECUTOR_API_KEY` to authenticated endpoints.
- **Memory endpoints return `Memory system not available` / `Memory system not initialized`.**
  - Fix: ensure the database is running, `DATABASE_URL` is set, and migrations have been applied before starting the API server.
- **Docker tests fail with host DNS errors (e.g., `nodename nor servname provided`).**
  - Fix: run the stack with `docker compose up -d` and re-run the tests, or run tests from inside the `l9-api` container as documented.

---

## PART II — CURSOR AI CONTRACT (CODE-MAP & PROTECTED SURFACE)

### MISSION

Enable safe, rapid AI-assisted development by:
1. Providing machine-readable code contracts via `CODE-MAP.yaml`
2. Enforcing protected surface boundaries (LCTO-controlled)
3. Automating docs-code consistency checks in CI/CD
4. Reducing cognitive load for human reviewers

---

### Subsystems (from CODE-MAP.yaml)

| Subsystem | Path | Allowed patterns | Protected |
|-----------|------|------------------|-----------|
| agents | core/agents | 8 allowed | 0 protected |
| memory | memory | 7 allowed | 0 protected |
| tools | core/tools | 6 allowed | 0 protected |
| api | api | 6 allowed | 0 protected |

**Before modifying:** Read `docs/CODE-MAP.yaml` for subsystem-specific `ai_allowed_patterns` and `ai_forbidden_patterns`.

---

### 🔒 PROTECTED (Never modify without explicit approval)

**These files are LCTO-controlled. Modifications require:**
1. Explicit TODO approval from L (CTO)
2. Risk assessment in the PR description
3. Rollback plan in case of issues

**Protected by LCTO (from policy / CODE-MAP):**


---

### Invariants (from CODE-MAP.yaml)

**agents:**
- Agent IDs are UUIDv4
- All agent tasks emit PacketEnvelope to memory substrate
- Kernel stack loaded via KernelLoader before execution
- Tool access mediated by RegistryAdapter with capability checks
- High-risk tools require Igor approval before dispatch

**memory:**
- All packet IDs are UUIDv4
- All timestamps are UTC ISO-8601
- PacketEnvelope is the canonical data structure for all memory writes
- Embeddings are list[float] with dimension 1536 or 3072
- Deduplication via dedup_key prevents duplicate ingestion

**tools:**
- Tool names must exist in L_TOOLS_DEFINITIONS registry
- Destructive tools require explicit approval gates
- All tool executions logged to PacketEnvelope audit trail
- Tool dispatch respects AgentCapabilities enum

**api:**
- Request/response schemas validated via Pydantic
- All logging is structured JSON with context (agent_id, task_id)
- WebSocket routes use websocket_orchestrator for lifecycle
- Rate limiting enforced via RateLimiter with Redis backend

**When implementing:** Verify your code maintains these invariants. If uncertain, ask L.

---

### HOW TO USE CODE-MAP.yaml

1. **Identify subsystem**: Is the file in `core/agents/`, `memory/`, `core/tools/`, `api/`?
2. **Check patterns**: Does the file match an `ai_allowed_pattern`?
3. **If YES**: Proceed normally
4. **If NO (matches forbidden)**: Stop and ask L (CTO) for approval
5. **If UNKNOWN**: Conservatively assume forbidden; ask for clarification

```bash
grep -A 20 "memory:" docs/CODE-MAP.yaml
```

---

### Regenerate CODE-MAP when code changes

```bash
python scripts/extract_code_facts.py
git diff docs/CODE-MAP.yaml
# Commit if intentional
```

---

### CHECKLIST: Before Submitting a PR

- [ ] Read `docs/CODE-MAP.yaml` for the subsystem I'm modifying
- [ ] Only modified files in `ai_allowed_patterns`
- [ ] No changes to protected files without explicit approval
- [ ] Ran `python scripts/extract_code_facts.py` if signatures changed
- [ ] Tests pass locally: `pytest tests/`
- [ ] PR description includes: What, Why, How (and risk assessment if protected)

---

### KEY CONTACTS

- **L (CTO):** Code architecture, protected file approvals, design decisions
- **Cursor (AI):** Implementation, testing, non-core logic
- **Igor (Boss):** Executive decisions, escalations

---

*Runbook generated by scripts/generate_runbook.py — refresh with --run-code-facts and/or --run-index.*
*L9 Secure AI OS | Architecture-Aware Development System*
