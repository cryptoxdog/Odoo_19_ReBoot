#!/usr/bin/env python3
"""
Extract Code Facts — universal repo scanner

Generates docs/CODE-MAP.yaml from Python AST analysis. Works in any repo:
- With config: uses config/subsystems/readme_config.yaml (and optional
  config/subsystems/code_facts_config.yaml for entrypoints/invariants).
- Without config: auto-discovers subsystems (Odoo modules, Python packages,
  and top-level dirs like docs, scripts, config).

Usage:
    python extract_code_facts.py
    python scripts/extract_code_facts.py

Output:
    - docs/CODE-MAP.yaml (subsystems, entrypoints when configured, classes, data models)

Config (optional):
    - config/subsystems/readme_config.yaml  → subsystems with path, title, purpose
    - config/subsystems/code_facts_config.yaml → entrypoint_class, entrypoint_method, invariants, ai_allowed_patterns per subsystem
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Extract Code Facts",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-18T02:07:37Z",
    "updated_at": "2026-01-18T02:07:37Z",
    "layer": "operations",
    "domain": ".dora",
    "module_name": "extract_code_facts",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import ast
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

try:
    import yaml
except ImportError:
    logger.error("error: pyyaml not installed. run: pip install pyyaml")
    sys.exit(1)


# ============================================================================
# Subsystem discovery and config (universal)
# ============================================================================

# Directories to skip when auto-discovering
SKIP_NAMES = frozenset({
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    ".tox", ".mypy_cache", ".ruff_cache", "dist", "build", "eggs", ".eggs",
})


def _normalize_subsystem(name: str, raw: dict, repo_root: Path) -> dict:
    """Normalize one subsystem entry: path, purpose, optional entrypoint/invariants."""
    path = raw.get("path", name)
    purpose = raw.get("purpose") or raw.get("description") or raw.get("title") or f"Subsystem: {path}"
    if isinstance(purpose, str):
        purpose = purpose.strip()
    out = {
        "path": path,
        "purpose": purpose,
        "entrypoint_class": raw.get("entrypoint_class"),
        "entrypoint_method": raw.get("entrypoint_method"),
        "ai_allowed_patterns": raw.get("ai_allowed_patterns") or [],
        "invariants": raw.get("invariants") or [],
    }
    return out


def load_readme_config(repo_root: Path) -> dict[str, dict]:
    """Load config/subsystems/readme_config.yaml if present."""
    path = repo_root / "config" / "subsystems" / "readme_config.yaml"
    if not path.exists() or not yaml:
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    subs = data.get("subsystems") or {}
    return {k: _normalize_subsystem(k, v, repo_root) for k, v in subs.items() if isinstance(v, dict) and v.get("path")}


def load_code_facts_config(repo_root: Path) -> dict[str, dict]:
    """Load config/subsystems/code_facts_config.yaml if present (overrides/extensions)."""
    path = repo_root / "config" / "subsystems" / "code_facts_config.yaml"
    if not path.exists() or not yaml:
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    subs = data.get("subsystems") or {}
    return {k: _normalize_subsystem(k, v, repo_root) for k, v in subs.items() if isinstance(v, dict) and v.get("path")}


def discover_subsystems(repo_root: Path) -> dict[str, dict]:
    """Auto-discover subsystems: Odoo modules (__manifest__.py), Python packages, and key top-level dirs."""
    out = {}
    # One level under root
    try:
        entries = sorted(repo_root.iterdir())
    except OSError:
        return out
    for p in entries:
        if not p.is_dir() or p.name.startswith(".") or p.name in SKIP_NAMES:
            continue
        rel = str(p.relative_to(repo_root))
        # Odoo module
        if (p / "__manifest__.py").exists():
            purpose = _read_manifest_name(p / "__manifest__.py") or f"Odoo module: {p.name}"
            out[p.name] = {"path": rel, "purpose": purpose, "entrypoint_class": None, "entrypoint_method": None, "ai_allowed_patterns": [], "invariants": []}
            continue
        # Python package (has __init__.py and at least one .py)
        if (p / "__init__.py").exists() and any(p.rglob("*.py")):
            out[p.name] = {"path": rel, "purpose": f"Python package: {p.name}", "entrypoint_class": None, "entrypoint_method": None, "ai_allowed_patterns": [], "invariants": []}
            continue
        # Known top-level dirs
        if p.name in ("docs", "scripts", "config", "tests", "tools", "infra"):
            out[p.name] = {"path": rel, "purpose": f"Repo {p.name}", "entrypoint_class": None, "entrypoint_method": None, "ai_allowed_patterns": [], "invariants": []}
    # One level under a single parent (e.g. Plasticos/foo)
    for p in entries:
        if not p.is_dir() or p.name.startswith(".") or p.name in SKIP_NAMES:
            continue
        try:
            subdirs = sorted(p.iterdir())
        except OSError:
            continue
        for q in subdirs:
            if not q.is_dir() or q.name.startswith(".") or q.name in SKIP_NAMES:
                continue
            if q.name in out:
                continue
            rel = str(q.relative_to(repo_root))
            if (q / "__manifest__.py").exists():
                purpose = _read_manifest_name(q / "__manifest__.py") or f"Odoo module: {q.name}"
                out[q.name] = {"path": rel, "purpose": purpose, "entrypoint_class": None, "entrypoint_method": None, "ai_allowed_patterns": [], "invariants": []}
            elif (q / "__init__.py").exists() and any(q.rglob("*.py")):
                out[q.name] = {"path": rel, "purpose": f"Python package: {q.name}", "entrypoint_class": None, "entrypoint_method": None, "ai_allowed_patterns": [], "invariants": []}
    return out


def _read_manifest_name(path: Path) -> str | None:
    """Read 'name' from __manifest__.py (Python dict or JSON)."""
    try:
        text = path.read_text().strip()
        if not text or not text.startswith("{"):
            return None
        # Try JSON first (Odoo 16+ style)
        try:
            import json
            data = json.loads(text)
            return data.get("name")
        except Exception:
            pass
        # Python dict literal
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for i, k in enumerate(node.keys):
                    if isinstance(k, ast.Constant) and k.value == "name" and i < len(node.values):
                        v = node.values[i]
                        if isinstance(v, ast.Constant):
                            return str(v.value)
                break
    except Exception:
        pass
    return None


def get_subsystems(repo_root: Path) -> dict[str, dict]:
    """Merge readme_config, code_facts_config, and discovery. Config wins; discovery fills gaps."""
    from_readme = load_readme_config(repo_root)
    from_facts = load_code_facts_config(repo_root)
    discovered = discover_subsystems(repo_root)
    # Start with discovery (works everywhere)
    merged = dict(discovered)
    # Overlay readme_config (path, purpose, tier, etc.)
    for k, v in from_readme.items():
        merged[k] = {**merged.get(k, {}), **v}
    # Overlay code_facts_config (entrypoint, invariants, ai_allowed_patterns)
    for k, v in from_facts.items():
        base = merged.get(k, {"path": v["path"], "purpose": v["purpose"], "entrypoint_class": None, "entrypoint_method": None, "ai_allowed_patterns": [], "invariants": []})
        merged[k] = {
            **base,
            "path": v.get("path") or base["path"],
            "purpose": v.get("purpose") or base["purpose"],
            "entrypoint_class": v.get("entrypoint_class") or base.get("entrypoint_class"),
            "entrypoint_method": v.get("entrypoint_method") or base.get("entrypoint_method"),
            "ai_allowed_patterns": v.get("ai_allowed_patterns") or base.get("ai_allowed_patterns") or [],
            "invariants": v.get("invariants") or base.get("invariants") or [],
        }
    return merged


# ============================================================================
# AST Extraction: Parse Python code for facts
# ============================================================================


class CodeFactExtractor:
    """Extract code facts using Python AST."""

    def __init__(self, repo_root: Path):
        """
        Initializes the CodeFactExtractor with the root directory of the repository for extracting code facts from Python AST.

        Args:
            repo_root: Path to the root directory of the code repository.

        Raises:
            ValueError: If the provided repo_root is not a valid directory.
        """
        self.repo_root = repo_root

    def extract_function_signature(self, node: ast.FunctionDef) -> str:
        """Extract function signature from AST node."""
        # Get argument names and types
        args = []
        for arg in node.args.args:
            args.append(arg.arg)

        # Get return type if annotated
        return_type = ""
        if node.returns:
            if isinstance(node.returns, ast.Name):
                return_type = f" -> {node.returns.id}"
            elif isinstance(node.returns, ast.Subscript):
                return_type = " -> [complex type]"

        return f"def {node.name}({', '.join(args)}){return_type}"

    def extract_class_info(self, filepath: Path, class_name: str) -> dict[str, Any]:
        """Extract class info: methods, docstring, line range."""
        try:
            content = filepath.read_text()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            methods.append(
                                {
                                    "name": item.name,
                                    "is_async": isinstance(item, ast.AsyncFunctionDef),
                                    "line": item.lineno,
                                }
                            )

                    return {
                        "name": class_name,
                        "file": str(filepath.relative_to(self.repo_root)),
                        "line_range": [node.lineno, node.end_lineno or node.lineno],
                        "methods": methods,
                        "docstring": ast.get_docstring(node) or "",
                    }
        except Exception as e:
            logger.warning(
                "warning: could not parse filepath: e", filepath=filepath, e=e
            )

        return {}

    def find_pydantic_models(self, subsystem_path: Path) -> list[dict[str, Any]]:
        """Find Pydantic dataclasses/models in subsystem."""
        models = []

        if not subsystem_path.exists():
            return models

        for py_file in subsystem_path.rglob("*.py"):
            try:
                content = py_file.read_text()
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    # Find dataclasses with field annotations
                    if isinstance(node, ast.ClassDef):
                        # Check if it has __dataclass__ or Pydantic decorators
                        is_dataclass = any(
                            (isinstance(dec, ast.Name) and dec.id == "dataclass")
                            or (isinstance(dec, ast.Name) and "Model" in dec.id)
                            for dec in node.decorator_list
                        )

                        if (
                            is_dataclass
                            or node.name.endswith("Result")
                            or node.name.endswith("Entry")
                        ):
                            fields = []
                            for item in node.body:
                                if isinstance(item, ast.AnnAssign) and isinstance(
                                    item.target, ast.Name
                                ):
                                    fields.append(item.target.id)

                            if fields:
                                models.append(
                                    {
                                        "name": node.name,
                                        "file": str(
                                            py_file.relative_to(self.repo_root)
                                        ),
                                        "fields": fields,
                                        "docstring": ast.get_docstring(node) or "",
                                    }
                                )
            except Exception as e:
                logger.warning(
                    "warning: could not parse py file: e", py_file=py_file, e=e
                )

        return models


def load_protected_files_policy(repo_root: Path) -> dict:
    """Load protected files policy from config."""
    policy_path = repo_root / "config/policies/protected_files.yaml"
    if not policy_path.exists():
        logger.warning(f"Policy file not found: {policy_path}")
        return {}
    with open(policy_path) as f:
        return yaml.safe_load(f) or {}


# ============================================================================
# CODE-MAP.yaml Generation
# ============================================================================


def generate_code_map(repo_root: Path, extractor: CodeFactExtractor, protected_policy: dict) -> dict[str, Any]:
    """Generate CODE-MAP.yaml structure from get_subsystems() and AST extraction."""
    code_map = {
        "version": "1.0",
        "last_verified": datetime.now(UTC).isoformat() + "Z",
        "global_protected_files": [],
        "subsystems": {},
    }

    # Populate global protected files from policy
    if protected_policy and "protected_files" in protected_policy:
        for item in protected_policy["protected_files"].get("lcto_controlled", []):
            code_map["global_protected_files"].append(item.get("path", item) if isinstance(item, dict) else item)
        for item in protected_policy["protected_files"].get("protected_patterns", []):
            code_map["global_protected_files"].append(item.get("pattern", item) if isinstance(item, dict) else item)

    subsystems = get_subsystems(repo_root)
    if not subsystems:
        logger.warning("No subsystems found (no config and discovery found nothing)")
        return code_map

    for subsystem_name, config in subsystems.items():
        path_str = config["path"]
        subsystem_path = repo_root / path_str
        if not subsystem_path.is_dir():
            logger.debug("Skipping missing path", subsystem=subsystem_name, path=path_str)
            continue

        entrypoint_info = {}
        entrypoint_class = config.get("entrypoint_class")
        if entrypoint_class:
            for py_file in subsystem_path.rglob("*.py"):
                class_info = extractor.extract_class_info(py_file, entrypoint_class)
                if class_info:
                    entrypoint_info = class_info
                    break

        models = extractor.find_pydantic_models(subsystem_path)
        subsystem_protected = []
        if protected_policy and "protected_files" in protected_policy and "subsystems" in protected_policy.get("protected_files", {}):
            sub_policy = protected_policy["protected_files"]["subsystems"].get(subsystem_name, {})
            subsystem_protected = sub_policy.get("files", [])

        entry_point = {
            "file": entrypoint_info.get("file", f"{path_str}/"),
            "class": entrypoint_class or "",
            "method": config.get("entrypoint_method") or "",
            "line_range": entrypoint_info.get("line_range", [1, 1]),
        }

        code_map["subsystems"][subsystem_name] = {
            "path": path_str,
            "purpose": config.get("purpose") or f"Subsystem: {path_str}",
            "entry_point": entry_point,
            "key_classes": [entrypoint_info] if entrypoint_info else [],
            "data_models": models,
            "protected_files": subsystem_protected,
            "ai_allowed_patterns": config.get("ai_allowed_patterns") or [],
            "ai_forbidden_patterns": subsystem_protected,
            "invariants": config.get("invariants") or [],
        }

    return code_map


# ============================================================================
# Main: Write files
# ============================================================================


def main():
    """Main entry point."""
    script_dir = Path(__file__).resolve().parent
    # If script lives at repo root (e.g. extract_code_facts.py), use script_dir; else scripts/ -> parent
    repo_root = script_dir if (script_dir / "docs").exists() or (script_dir / "config").exists() else script_dir.parent
    docs_dir = repo_root / "docs"
    docs_dir.mkdir(exist_ok=True)

    logger.info("Extracting code facts...", repo_root=str(repo_root))

    extractor = CodeFactExtractor(repo_root)
    protected_policy = load_protected_files_policy(repo_root)

    # Generate CODE-MAP.yaml
    logger.info("Generating docs/CODE-MAP.yaml...")
    code_map = generate_code_map(repo_root, extractor, protected_policy)

    code_map_path = docs_dir / "CODE-MAP.yaml"
    with open(code_map_path, "w") as f:
        yaml.dump(code_map, f, default_flow_style=False, sort_keys=False)
    logger.info("Generated", path=str(code_map_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": ".DO-OPER-002",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        ".dora",
        "api",
        "ast",
        "auth",
        "cli",
        "config",
        "filesystem",
        "operations",
        "realtime",
        "rest-api",
    ],
    "keywords": [
        "extract",
        "extractor",
        "fact",
        "facts",
        "find",
        "function",
        "generate",
        "map",
    ],
    "business_value": "This script is the SOURCE OF TRUTH for AI-facing contracts. python scripts/extract_code_facts.py docs/CODE-MAP.yaml (subsystems, entrypoints, classes, schemas, invariants) l9/core/agents/README.meta.y",
    "last_modified": "2026-01-18T02:07:37Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
