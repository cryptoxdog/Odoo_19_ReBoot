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

        self.assertIsInstance(intake.match_response, dict)
        ranked = intake.match_response.get("ranked_buyers", [])
        self.assertIsInstance(ranked, list)
        for buyer in ranked:
            score = buyer.get("score")
            self.assertIsNotNone(score)
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

        self.assert_trace_created()


