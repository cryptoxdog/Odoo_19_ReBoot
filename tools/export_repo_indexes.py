#!/usr/bin/env python3
"""
Export repo indexes for fast lookup.

Writes to reports/repo-index/ in the repo root (detected from cwd, L9_REPO_ROOT, or git).
Indexes: readme_manifest, class_definitions, function_signatures, imports, route_handlers,
test_catalog, inheritance_graph, method_catalog, pydantic_models, env_refs.

Usage:
  python3 tools/export_repo_indexes.py
  L9_REPO_ROOT=/path/to/repo python3 tools/export_repo_indexes.py
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
from pathlib import Path


def get_repo_root() -> Path:
    root = os.environ.get("L9_REPO_ROOT")
    if root:
        return Path(root).resolve()
    cwd = Path.cwd().resolve()
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip()).resolve()
    except Exception:
        pass
    return cwd


SKIP_DIRS = {".git", "__pycache__", "venv", ".venv", "env", "node_modules", ".tox", "htmlcov"}


def should_skip(path: Path, repo_root: Path) -> bool:
    rel = path.relative_to(repo_root) if path.is_relative_to(repo_root) else path
    parts = rel.parts
    return any(p in SKIP_DIRS for p in parts)


# ---------------------------------------------------------------------------
# README manifest
# ---------------------------------------------------------------------------


def collect_readmes(repo_root: Path) -> list[tuple[str, str]]:
    out = []
    for p in repo_root.rglob("README*"):
        if not p.is_file() or should_skip(p, repo_root):
            continue
        try:
            text = p.read_text(errors="replace")
            first = text.split("\n\n")[0].strip()[:200] if text else ""
            rel = str(p.relative_to(repo_root))
            out.append((rel, first))
        except Exception:
            pass
    return sorted(out, key=lambda x: x[0])


# ---------------------------------------------------------------------------
# Env var refs (for generate_runbook and env_refs.txt)
# ---------------------------------------------------------------------------


def collect_env_refs(repo_root: Path) -> set[str]:
    pattern = re.compile(
        r"os\.environ(?:\.get)?\s*\(\s*[\"']([^\"']+)[\"']"
        r"|os\.getenv\s*\(\s*[\"']([^\"']+)[\"']"
        r"|environ\.get\s*\(\s*[\"']([^\"']+)[\"']"
        r"|[\"']([A-Z][A-Z0-9_]{2,})[\"']\s*[:=].*\.env",
        re.MULTILINE,
    )
    refs = set()
    for p in repo_root.rglob("*.py"):
        if should_skip(p, repo_root):
            continue
        try:
            text = p.read_text(errors="replace")
            for m in pattern.finditer(text):
                for g in m.groups():
                    if g and g.isupper():
                        refs.add(g)
        except Exception:
            pass
    for p in list(repo_root.rglob("*.yaml")) + list(repo_root.rglob("*.yml")):
        if not p.is_file() or should_skip(p, repo_root):
            continue
        try:
            text = p.read_text(errors="replace")
            for m in re.finditer(r"[\"']([A-Z][A-Z0-9_]{2,})[\"']", text):
                refs.add(m.group(1))
        except Exception:
            pass
    return refs


# ---------------------------------------------------------------------------
# Python AST: classes, functions, imports, routes, tests, inheritance, methods, pydantic
# ---------------------------------------------------------------------------


def collect_python_indexes(repo_root: Path) -> dict:
    classes = []
    functions = []
    imports = []
    routes = []
    tests = []
    inheritance = []
    methods = []
    pydantic_models = []

    for py_path in repo_root.rglob("*.py"):
        if should_skip(py_path, repo_root):
            continue
        rel = str(py_path.relative_to(repo_root))
        try:
            text = py_path.read_text(errors="replace")
            tree = ast.parse(text)
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append((rel, node.lineno, node.name))
                for b in node.bases:
                    name = ast.get_source_segment(text, b) or get_attr_name(b)
                    if name and name != "object":
                        inheritance.append((rel, node.lineno, node.name, name))
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append((rel, node.name, item.name, item.lineno))
                if any(
                    isinstance(d, ast.Name) and ("Model" in d.id or d.id == "BaseModel")
                    for d in node.decorator_list
                ) or (node.name.endswith("Model") and has_annotations(node)):
                    fields = [getattr(a.target, "id", "") for a in node.body if isinstance(a, ast.AnnAssign) and hasattr(a.target, "id")]
                    pydantic_models.append((rel, node.lineno, node.name, ",".join(fields)))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                sig = f"def {node.name}(...)"
                functions.append((rel, node.lineno, sig))
                if "test" in node.name.lower() or (node.name.startswith("test_") and has_test_decorator(node)):
                    tests.append((rel, node.lineno, node.name))
                route = get_route_decorator(node, text)
                if route:
                    routes.append((rel, node.lineno, route))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((rel, node.lineno, alias.name, ""))
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    imports.append((rel, node.lineno, mod, alias.name))

    return {
        "classes": classes,
        "functions": functions,
        "imports": imports,
        "routes": routes,
        "tests": tests,
        "inheritance": inheritance,
        "methods": methods,
        "pydantic_models": pydantic_models,
    }


def get_attr_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{get_attr_name(node.value)}.{node.attr}"
    return ""


def has_annotations(node: ast.ClassDef) -> bool:
    return any(isinstance(b, ast.AnnAssign) for b in node.body)


def has_test_decorator(node: ast.FunctionDef) -> bool:
    for d in node.decorator_list:
        if isinstance(d, ast.Name) and "test" in d.id.lower():
            return True
        if isinstance(d, ast.Attribute) and "test" in d.attr.lower():
            return True
    return False


def get_route_decorator(node: ast.FunctionDef, source: str) -> str | None:
    for d in node.decorator_list:
        if isinstance(d, ast.Call):
            name = ""
            if isinstance(d.func, ast.Name):
                name = d.func.id
            elif isinstance(d.func, ast.Attribute):
                name = d.func.attr
            if name in ("get", "post", "put", "patch", "delete", "route"):
                method = name.upper()
                if d.args and isinstance(d.args[0], ast.Constant):
                    path = d.args[0].value
                    return f"{method} {path}"
                seg = ast.get_source_segment(source, d)
                if seg:
                    return f"{method} {seg[:60]}"
    return None


# ---------------------------------------------------------------------------
# Write index files
# ---------------------------------------------------------------------------


def write_index(out_dir: Path, name: str, lines: list[str]) -> int:
    path = out_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(lines)


def main() -> int:
    repo_root = get_repo_root()
    out_dir = repo_root / "reports" / "repo-index"
    out_dir.mkdir(parents=True, exist_ok=True)

    # README manifest
    readmes = collect_readmes(repo_root)
    write_index(
        out_dir,
        "readme_manifest.txt",
        [f"PATH: {p} | DESC: {d}" for p, d in readmes],
    )

    # Env refs (one name per line for generate_runbook)
    env_refs = sorted(collect_env_refs(repo_root))
    write_index(out_dir, "env_refs.txt", env_refs)

    # Python indexes
    data = collect_python_indexes(repo_root)
    n_classes = write_index(
        out_dir,
        "class_definitions.txt",
        [f"{p}:{ln} {c}" for p, ln, c in data["classes"]],
    )
    n_funcs = write_index(
        out_dir,
        "function_signatures.txt",
        [f"{p}:{ln} {s}" for p, ln, s in data["functions"]],
    )
    write_index(
        out_dir,
        "imports.txt",
        [f"{p}:{ln} {m} -> {n}" for p, ln, m, n in data["imports"]],
    )
    n_routes = write_index(
        out_dir,
        "route_handlers.txt",
        [f"{p}:{ln} {r}" for p, ln, r in data["routes"] if r],
    )
    n_tests = write_index(
        out_dir,
        "test_catalog.txt",
        [f"{p}:{ln} {t}" for p, ln, t in data["tests"]],
    )
    write_index(
        out_dir,
        "inheritance_graph.txt",
        [f"{p}:{ln} {c} -> {b}" for p, ln, c, b in data["inheritance"]],
    )
    write_index(
        out_dir,
        "method_catalog.txt",
        [f"{p} {cls}.{m} L{ln}" for p, cls, m, ln in data["methods"]],
    )
    write_index(
        out_dir,
        "pydantic_models.txt",
        [f"{p}:{ln} {n} ({f})" for p, ln, n, f in data["pydantic_models"]],
    )

    print("## INDEX UPDATED")
    print()
    print("| Index | Entries |")
    print("|-------|--------|")
    print(f"| readmes | {len(readmes)} |")
    print(f"| env_refs | {len(env_refs)} |")
    print(f"| classes | {n_classes} |")
    print(f"| functions | {n_funcs} |")
    print(f"| routes | {n_routes} |")
    print(f"| tests | {n_tests} |")
    print()
    print("**Location:** reports/repo-index/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
