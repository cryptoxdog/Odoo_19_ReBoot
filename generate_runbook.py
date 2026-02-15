#!/usr/bin/env python3
"""
Generate docs/CURSOR-RUNBOOK.md from Makefile, CODE-MAP.yaml, and repo-index.

Uses:
  - scripts/extract_code_facts.py (optional: run to refresh CODE-MAP.yaml)
  - tools/export_repo_indexes.py (optional: run to refresh reports/repo-index)
  - docs/CODE-MAP.yaml (subsystems, protected, invariants)
  - config/policies/protected_files.yaml (LCTO-controlled list)
  - reports/repo-index/env_refs.txt (env var names)
  - Makefile (make help → ops commands)

Usage:
  python scripts/generate_runbook.py
  python scripts/generate_runbook.py --run-code-facts --run-index
  python scripts/generate_runbook.py --run-index
  python scripts/generate_runbook.py --dry-run
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

try:
    import yaml
except ImportError:
    yaml = None


def get_repo_root() -> Path:
    script_dir = Path(__file__).resolve().parent
    if (script_dir / "docs").exists() or (script_dir / "config").exists() or (script_dir / "Makefile").exists():
        return script_dir
    return script_dir.parent


def run_code_facts(repo_root: Path) -> bool:
    script = repo_root / "scripts" / "extract_code_facts.py"
    if not script.exists():
        logger.warning("extract_code_facts not found", path=str(script))
        return False
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        logger.warning("extract_code_facts failed", stderr=result.stderr)
        return False
    logger.info("extract_code_facts completed")
    return True


def run_repo_index(repo_root: Path) -> bool:
    script = repo_root / "tools" / "export_repo_indexes.py"
    if not script.exists():
        logger.warning("export_repo_indexes not found", path=str(script))
        return False
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        logger.warning("export_repo_indexes failed", stderr=result.stderr)
        return False
    logger.info("export_repo_indexes completed")
    return True


_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")

def get_make_help(repo_root: Path) -> str:
    result = subprocess.run(
        ["make", "help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        return "# make help failed (run manually: make help)\n"
    return _ANSI_ESCAPE.sub("", result.stdout)


def load_code_map(repo_root: Path) -> dict | None:
    path = repo_root / "docs" / "CODE-MAP.yaml"
    if not path.exists():
        logger.warning("CODE-MAP.yaml not found", path=str(path))
        return None
    if not yaml:
        logger.error("pyyaml required; pip install pyyaml")
        return None
    with open(path) as f:
        return yaml.safe_load(f)


def load_protected_policy(repo_root: Path) -> dict:
    path = repo_root / "config" / "policies" / "protected_files.yaml"
    if not path.exists() or not yaml:
        return {}
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return data.get("protected_files", {})


def get_env_vars_from_index(repo_root: Path) -> list[str]:
    path = repo_root / "reports" / "repo-index" / "env_refs.txt"
    if not path.exists():
        return []
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("="):
                continue
            out.append(line)
    return sorted(set(out))


def get_required_env_docs() -> list[str]:
    return ["DATABASE_URL", "L9_EXECUTOR_API_KEY"]


def build_part1_ops(make_help: str, env_vars: list[str], required: list[str]) -> str:
    required_block = "\n".join(f"- `{v}`" for v in required)
    env_block = "\n".join(f"- `{v}`" for v in env_vars[:40]) if env_vars else required_block
    if len(env_vars) > 40:
        env_block += f"\n- _... and {len(env_vars) - 40} more (see reports/repo-index/env_refs.txt)_"
    make_block = "\n".join("    " + line for line in make_help.strip().split("\n"))
    return f"""## PART I — OPERATIONS (RUN THE STACK)

### Make targets (from `make help`)

```bash
{make_block}
```

### Required environment variables (names)

{required_block}

### All env vars referenced in repo (from repo-index)

{env_block}

### Common failure modes + fixes

- **API requests return `Executor key not configured` or `Unauthorized`.**
  - Fix: set `L9_EXECUTOR_API_KEY` and pass `Authorization: Bearer $L9_EXECUTOR_API_KEY` to authenticated endpoints.
- **Memory endpoints return `Memory system not available` / `Memory system not initialized`.**
  - Fix: ensure the database is running, `DATABASE_URL` is set, and migrations have been applied before starting the API server.
- **Docker tests fail with host DNS errors (e.g., `nodename nor servname provided`).**
  - Fix: run the stack with `docker compose up -d` and re-run the tests, or run tests from inside the `l9-api` container as documented.
"""


def build_part2_contract(code_map: dict | None, protected: dict) -> str:
    if not code_map:
        return _part2_static_only(protected)

    subsystems = code_map.get("subsystems", {})
    global_protected = code_map.get("global_protected_files", [])

    # Subsystem table
    rows = []
    for name, sub in subsystems.items():
        path = sub.get("path", "")
        allowed = sub.get("ai_allowed_patterns", [])
        forbidden = sub.get("ai_forbidden_patterns", sub.get("protected_files", []))
        rows.append(f"| {name} | {path} | {len(allowed)} allowed | {len(forbidden)} protected |")

    subs_table = "\n".join(rows) if rows else "| (none) | | | |"

    # Protected list (LCTO from policy if available, else from CODE-MAP)
    lcto_paths = []
    if "lcto_controlled" in protected:
        for item in protected["lcto_controlled"]:
            if isinstance(item, dict) and "path" in item:
                lcto_paths.append(item["path"])
            elif isinstance(item, str):
                lcto_paths.append(item)
    if not lcto_paths and global_protected:
        lcto_paths = global_protected[:20]
    protected_bullets = "\n".join(f"- `{p}`" for p in lcto_paths)

    # Invariants by subsystem
    inv_lines = []
    for name, sub in subsystems.items():
        invs = sub.get("invariants", [])
        if invs:
            inv_lines.append(f"**{name}:**")
            for i in invs:
                inv_lines.append(f"- {i}")
            inv_lines.append("")
    invariants_block = "\n".join(inv_lines).strip() if inv_lines else "(See docs/CODE-MAP.yaml per subsystem.)"

    return f"""## PART II — CURSOR AI CONTRACT (CODE-MAP & PROTECTED SURFACE)

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
{subs_table}

**Before modifying:** Read `docs/CODE-MAP.yaml` for subsystem-specific `ai_allowed_patterns` and `ai_forbidden_patterns`.

---

### 🔒 PROTECTED (Never modify without explicit approval)

**These files are LCTO-controlled. Modifications require:**
1. Explicit TODO approval from L (CTO)
2. Risk assessment in the PR description
3. Rollback plan in case of issues

**Protected by LCTO (from policy / CODE-MAP):**
{protected_bullets}

---

### Invariants (from CODE-MAP.yaml)

{invariants_block}

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
"""


def _part2_static_only(protected: dict) -> str:
    lcto_paths = []
    if isinstance(protected, dict) and "lcto_controlled" in protected:
        for item in protected["lcto_controlled"]:
            if isinstance(item, dict) and "path" in item:
                lcto_paths.append(item["path"])
    protected_bullets = "\n".join(f"- `{p}`" for p in lcto_paths) if lcto_paths else "- (Run extract_code_facts and generate_runbook with CODE-MAP.yaml present.)"
    return f"""## PART II — CURSOR AI CONTRACT (CODE-MAP & PROTECTED SURFACE)

### MISSION

Enable safe, rapid AI-assisted development via `docs/CODE-MAP.yaml` and protected surface enforcement.

### 🔒 PROTECTED (LCTO-controlled)

{protected_bullets}

### Regenerate CODE-MAP and runbook

```bash
python scripts/extract_code_facts.py
python scripts/generate_runbook.py --run-code-facts
```

---

*Runbook generated by scripts/generate_runbook.py (CODE-MAP.yaml missing or unreadable).*
*L9 Secure AI OS*
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate docs/CURSOR-RUNBOOK.md from Makefile, CODE-MAP, repo-index."
    )
    parser.add_argument(
        "--run-code-facts",
        action="store_true",
        help="Run scripts/extract_code_facts.py before generating (refresh CODE-MAP.yaml)",
    )
    parser.add_argument(
        "--run-index",
        action="store_true",
        help="Run tools/export_repo_indexes.py before generating (refresh reports/repo-index)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write docs/CURSOR-RUNBOOK.md",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: docs/CURSOR-RUNBOOK.md)",
    )
    args = parser.parse_args()

    repo_root = get_repo_root()
    if args.run_code_facts:
        run_code_facts(repo_root)
    if args.run_index:
        run_repo_index(repo_root)

    make_help = get_make_help(repo_root)
    code_map = load_code_map(repo_root)
    protected = load_protected_policy(repo_root)
    env_vars = get_env_vars_from_index(repo_root)
    required = get_required_env_docs()

    part1 = build_part1_ops(make_help, env_vars, required)
    part2 = build_part2_contract(code_map, protected)

    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    header = f"""# CURSOR-RUNBOOK.md

**For:** Cursor IDE / AI Pair Programming + developers running L9  
**Audience:** Cursor AI Assistant, developers, ops  
**Authority:** L (CTO), Igor (Boss)  
**Generated:** {generated_at} by `scripts/generate_runbook.py`  
**Status:** READY FOR PHASE 2 IMPLEMENTATION

---

"""

    content = header + part1 + "\n---\n\n" + part2

    out_path = args.output or (repo_root / "docs" / "CURSOR-RUNBOOK.md")
    if args.dry_run:
        logger.info("dry_run", output_path=str(out_path), length=len(content))
        print(content[:2000] + "\n... [truncated]")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    logger.info("runbook_generated", path=str(out_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
