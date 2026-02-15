Plasticos/
└── tests/
    ├── __init__.py
    ├── base_test_case.py
    ├── test_full_replay.py
    ├── test_buyer_matching_matrix.py
    └── canonical_intake_templates.py

No UI.
All deterministic.
Replay-ready.
CI-safe.

⸻

FILE: Plasticos/tests/__init__.py

from . import base_test_case
from . import test_full_replay
from . import test_buyer_matching_matrix


⸻

FILE: Plasticos/tests/base_test_case.py

from odoo.tests.common import TransactionCase


class PlasticosBaseTest(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.Partner = cls.env["res.partner"]
        cls.Intake = cls.env["plasticos.intake"]
        cls.MaterialProfile = cls.env["plasticos.material.profile"]
        cls.TraceRun = cls.env["l9.trace.run"]

    def create_partner(self, name="Test Supplier"):
        return self.Partner.create({"name": name})

    def create_intake(self, partner, payload):
        payload.update({"partner_id": partner.id})
        return self.Intake.create(payload)

    def assert_trace_created(self):
        count = self.TraceRun.search_count([])
        self.assertGreater(count, 0, "Trace run not created")


⸻

FILE: Plasticos/tests/canonical_intake_templates.py

CANONICAL_INTAKES = {

    "pp_regrind_medical": {
        "name": "PP Regrind Medical",
        "polymer": "PP",
        "form": "regrind",
        "color": "natural",
        "source_type": "post-industrial",
        "grade_hint": "homopolymer",
        "mfi_value": 10.0,
        "density_value": 0.9,
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
    },

    "hdpe_drum_grind": {
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
    },

    "abs_fr_regrind": {
        "name": "ABS FR Regrind",
        "polymer": "ABS",
        "form": "regrind",
        "color": "black",
        "source_type": "post-industrial",
        "grade_hint": "FR grade",
        "mfi_value": 15,
        "density_value": 1.05,
        "moisture_ppm": 300,
        "contamination_total_pct": 1.0,
        "has_metal": False,
        "has_fr": True,
        "has_residue": False,
        "filler_type": "talc",
        "filler_pct": 10.0,
        "origin_application": "electronics housings",
        "origin_sector": "consumer_goods",
        "origin_process_type": "injection",
        "quantity_per_load_lbs": 42000,
        "loads_per_month": 3,
        "deal_type": "ongoing",
    },
}


⸻

FILE: Plasticos/tests/test_full_replay.py

from .base_test_case import PlasticosBaseTest
from .canonical_intake_templates import CANONICAL_INTAKES


class TestFullReplay(PlasticosBaseTest):

    def test_happy_path_replay(self):

        partner = self.create_partner("Replay Supplier")

        payload = CANONICAL_INTAKES["pp_regrind_medical"]

        intake = self.create_intake(partner, payload)

        self.assertTrue(intake.id)

        # Simulate adapter execution
        adapter = self.env["l9.adapter.service"]
        adapter.run_buyer_match(intake)

        intake.refresh()

        self.assertIn(
            intake.match_status,
            ["matched", "rejected"]
        )

        self.assert_trace_created()


⸻

FILE: Plasticos/tests/test_buyer_matching_matrix.py

from .base_test_case import PlasticosBaseTest
from .canonical_intake_templates import CANONICAL_INTAKES


class TestBuyerMatchingMatrix(PlasticosBaseTest):

    def test_multiple_material_variations(self):

        partner = self.create_partner("Matrix Supplier")

        adapter = self.env["l9.adapter.service"]

        for key, payload in CANONICAL_INTAKES.items():

            intake = self.create_intake(partner, payload)

            adapter.run_buyer_match(intake)

            intake.refresh()

            self.assertIn(
                intake.match_status,
                ["matched", "rejected"]
            )

        self.assert_trace_created()