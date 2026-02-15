#!/usr/bin/env python3
"""
Generate subsystem READMEs from config/subsystems/readme_config.yaml.
Supports: --list, --validate, --skip-time-verify, --subsystem, --tier.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

# Repo root: script lives in scripts/
REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "subsystems" / "readme_config.yaml"

README_TEMPLATE = """---
component_id: "{component_id}"
component_name: "{title}"
module_version: "1.0.0"
layer: "{tier}"
domain: "plasticos"
type: "subsystem"
status: "active"
purpose: "{purpose}"
summary: "{description}"
---

# {title}

## Purpose
{purpose}

## Summary
{description}

## Structure
```
{structure}
```

## Tier
{tier}
"""


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print(f"[ERROR] Config not found: {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    if yaml is None:
        print("[ERROR] PyYAML required: pip install pyyaml", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_subsystems(config: dict, subsystem_filter: str | None = None, tier_filter: str | None = None) -> dict:
    raw = config.get("subsystems") or {}
    out = {}
    for key, val in raw.items():
        if isinstance(val, dict):
            if subsystem_filter and key != subsystem_filter:
                continue
            if tier_filter and val.get("tier") != tier_filter:
                continue
            out[key] = val
    return out


def subdirs_structure(path: Path, max_depth: int = 1) -> str:
    if not path.is_dir():
        return "(not a directory)"
    lines = []
    try:
        children = sorted(p for p in path.iterdir() if not p.name.startswith(".") and p.name != "__pycache__")
    except OSError:
        return "(unreadable)"
    for i, p in enumerate(children):
        branch = "└── " if i == len(children) - 1 else "├── "
        lines.append(branch + p.name)
    return "\n".join(lines) if lines else "(empty)"


def component_id(tier: str, name: str) -> str:
    tier_map = {"core": "CORE", "orchestration": "ORC", "infrastructure": "INF"}
    pre = tier_map.get(tier, "SUB")
    slug = name.upper().replace(" ", "_").replace("-", "_")[:20]
    return f"{pre}-{slug}-001"


def generate_one(root: Path, key: str, cfg: dict) -> bool:
    rel = cfg.get("path", key)
    target_dir = root / rel
    if not target_dir.is_dir():
        return False
    title = cfg.get("title", key.replace("_", " ").title())
    purpose = cfg.get("purpose", "See config.")
    description = cfg.get("description", purpose)
    tier = cfg.get("tier", "infrastructure")
    structure = subdirs_structure(target_dir)
    cid = component_id(tier, key)
    content = README_TEMPLATE.format(
        component_id=cid,
        title=title,
        purpose=purpose,
        description=description,
        tier=tier,
        structure=structure,
    )
    readme = target_dir / "README.md"
    readme.write_text(content, encoding="utf-8")
    return True


def cmd_list(config: dict) -> None:
    subs = get_subsystems(config)
    print(f"Subsystems in config: {len(subs)}")
    for k, v in subs.items():
        path = v.get("path", k)
        print(f"  - {k}: {path}")


def cmd_validate(config: dict, root: Path) -> int:
    subs = get_subsystems(config)
    errors = 0
    for k, v in subs.items():
        path = root / v.get("path", k)
        readme = path / "README.md"
        if not path.is_dir():
            print(f"[MISS] {k}: path does not exist: {path}")
            errors += 1
        elif not readme.is_file():
            print(f"[NO README] {k}: {readme}")
            errors += 1
        else:
            print(f"[OK] {k}")
    return errors


def cmd_generate(config: dict, root: Path, skip_time_verify: bool, subsystem: str | None, tier: str | None) -> None:
    subs = get_subsystems(config, subsystem_filter=subsystem, tier_filter=tier)
    generated = 0
    skipped = 0
    for k, v in subs.items():
        rel = v.get("path", k)
        if not (root / rel).is_dir():
            skipped += 1
            continue
        if generate_one(root, k, v):
            generated += 1
    print(f"Generated: {generated}")
    print(f"Skipped (missing dir): {skipped}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate subsystem READMEs from readme_config.yaml")
    ap.add_argument("--list", action="store_true", help="List subsystems in config")
    ap.add_argument("--validate", action="store_true", help="Validate paths and README presence")
    ap.add_argument("--skip-time-verify", action="store_true", help="Skip timestamp checks (for generate)")
    ap.add_argument("--subsystem", type=str, help="Only process this subsystem")
    ap.add_argument("--tier", type=str, help="Only process this tier")
    args = ap.parse_args()

    config = load_config()
    root = REPO_ROOT

    if args.list:
        cmd_list(config)
        return 0
    if args.validate:
        n = cmd_validate(config, root)
        return 1 if n else 0
    cmd_generate(config, root, args.skip_time_verify, args.subsystem, args.tier)
    return 0


if __name__ == "__main__":
    sys.exit(main())
