from odoo.tests.common import TransactionCase


class TestModuleInstall(TransactionCase):

    def test_models_exist(self):
        models = [
            "plasticos.transaction",
            "plasticos.commission.rule",
            "plasticos.document",
        ]
        for m in models:
            self.assertTrue(self.env["ir.model"].search([("model", "=", m)]))
