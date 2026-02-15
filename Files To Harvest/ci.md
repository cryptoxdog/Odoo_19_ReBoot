
A) Pre-commit enforcement (adapter is the only border)
FILE: .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: block-network-calls-outside-adapter
        name: Block direct network calls outside l9_adapter
        entry: python3 scripts/precommit_block_forbidden_calls.py
        language: system
        pass_filenames: false

      - id: basic-python-syntax
        name: Basic python compile check
        entry: python3 -m compileall -q Plasticos
        language: system
        pass_filenames: false
FILE: scripts/precommit_block_forbidden_calls.py
import os
import re
import sys

ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
PLASTICOS = os.path.join(ROOT, "Plasticos")

FORBIDDEN = [
    r"\brequests\.",
    r"\bhttpx\.",
    r"\burllib3\.",
    r"\burllib\.request\b",
]

ALLOW_DIRS = {
    os.path.join(PLASTICOS, "l9_adapter"),
}

def is_allowed(path: str) -> bool:
    ap = os.path.abspath(path)
    for a in ALLOW_DIRS:
        if ap.startswith(os.path.abspath(a) + os.sep) or ap == os.path.abspath(a):
            return True
    return False

def main() -> int:
    bad = []
    for base, _, files in os.walk(PLASTICOS):
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(base, fn)
            if is_allowed(path):
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                txt = f.read()
            for pat in FORBIDDEN:
                if re.search(pat, txt):
                    bad.append((path, pat))
    if bad:
        print("FORBIDDEN network call patterns found outside Plasticos/l9_adapter:")
        for p, pat in bad:
            print(f"- {p}  (pattern: {pat})")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
B) CI workflow to run replay tests (no clicking)
FILE: .github/workflows/odoo_ci.yml
name: Odoo CI (Replay Tests)

on:
  push:
  pull_request:

jobs:
  replay-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: odoo
          POSTGRES_PASSWORD: odoo
          POSTGRES_DB: odoo
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U odoo -d odoo"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 20

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install deps
        run: |
          python -m pip install -U pip wheel
          # Adjust these to your repo's Odoo install method
          pip install -r requirements.txt || true

      - name: Run Odoo tests
        env:
          PGHOST: 127.0.0.1
          PGPORT: 5432
          PGUSER: odoo
          PGPASSWORD: odoo
        run: |
          # Replace with your repo’s real Odoo test command.
          # Typical shape:
          # odoo-bin -d odoo --stop-after-init -i l9_trace,plasticos_material,plasticos_processing,plasticos_intake,l9_adapter --test-enable --log-level=test
          echo "TODO: wire to your repo's odoo-bin invocation"
          exit 1
(Next pass I’ll patch this to the exact odoo-bin command once we align to your repo entrypoint path.)

C) Canonical replay runner (CLI, deterministic)
FILE: scripts/replay_intake_matrix.py
"""
Run inside: odoo shell -d <db> < scripts/replay_intake_matrix.py
Assumes env is available (odoo shell provides it).
"""

from datetime import datetime

TEMPLATES = [
    {
        "name": "PP Regrind Medical",
        "polymer": "PP",
        "form": "regrind",
        "color": "natural",
        "source_type": "post-industrial",
        "grade_hint": "homopolymer",
        "mfi_value": 10.0,
        "density_value": 0.90,
        "moisture_ppm": 200,
        "contamination_total_pct": 0.5,
        "has_metal": False,
        "has_fr": False,
        "has_residue": False,
        "filler_type": "none",
        "filler_pct": 0.0,
        "origin_application": "medical trays",
        "origin_sector": "medical",
        "origin_process_type": "injection",
        "quantity_per_load_lbs": 40000,
        "loads_per_month": 4,
        "deal_type": "ongoing",
        "material_hint_text": "Natural PP regrind from medical trays, clean, flows ~10."
    },
    {
        "name": "HDPE Drum Grind",
        "polymer": "HDPE",
        "form": "grind",
        "color": "mixed",
        "source_type": "post-consumer",
        "grade_hint": "",
        "mfi_value": 0.3,
        "density_value": 0.95,
        "moisture_ppm": 800,
        "contamination_total_pct": 2.0,
        "has_metal": True,
        "has_fr": False,
        "has_residue": True,
        "filler_type": "unknown",
        "filler_pct": 0.0,
        "origin_application": "chemical drums",
        "origin_sector": "industrial",
        "origin_process_type": "blow_molding",
        "quantity_per_load_lbs": 38000,
        "loads_per_month": 2,
        "deal_type": "spot",
        "material_hint_text": "HDPE drum grind, some residue, possible metal clips."
    },
]

Partner = env["res.partner"]
Intake = env["plasticos.intake"]

partner = Partner.create({"name": f"ReplayMatrix {datetime.utcnow().isoformat()}"})

try:
    adapter = env["l9.adapter.service"]
except Exception:
    adapter = None

created = []
for t in TEMPLATES:
    vals = dict(t)
    vals["partner_id"] = partner.id
    intake = Intake.create(vals)
    created.append(intake.id)

    print(f"\nCreated intake #{intake.id} {intake.name} ({intake.polymer}/{intake.form})")

    if adapter:
        adapter.run_buyer_match(intake)

        intake.refresh()
        print(f"Match status: {intake.match_status}")
        # match_response may be empty until adapter exists / L9 connected
        print(f"Has match_response: {bool(intake.match_response)}")
    else:
        print("Adapter not installed yet: skipping match call.")

print("\nDone. Intake IDs:", created)
print("Trace runs:", env["l9.trace.run"].search_count([]))




D) Build l9_adapter module (new) with strict boundary + trace hooks
This is a drop-in module. It will compile even before L9 is live.
It provides:

deterministic packet build

packet_version

trace integration

strict writeback (only match fields)

stubs for idempotency + replay (we’ll wire to intake storage via patches next pass)
