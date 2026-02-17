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

            ranked = intake.match_response.get("ranked_buyers", [])
            self.assertIsInstance(ranked, list)
            for buyer in ranked:
                score = buyer.get("score")
                self.assertIsNotNone(score)
                self.assertGreaterEqual(score, 0.0)
                self.assertLessEqual(score, 1.0)

        self.assert_trace_created()