from odoo.tests.common import TransactionCase


class TestTraceCoverage(TransactionCase):

    def test_trace_model_exists(self):
        model = self.env["ir.model"].search([
            ("model", "=", "l9.trace.run")
        ])
        self.assertTrue(model)
