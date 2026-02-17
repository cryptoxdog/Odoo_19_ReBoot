from odoo.tests.common import TransactionCase


class TestUpgradeSafety(TransactionCase):

    def test_sequence_exists(self):
        seq = self.env["ir.sequence"].search([
            ("code", "=", "plasticos.transaction")
        ])
        self.assertTrue(seq)
