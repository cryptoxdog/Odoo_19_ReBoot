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



