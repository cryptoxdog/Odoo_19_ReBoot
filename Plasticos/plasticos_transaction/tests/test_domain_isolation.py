from odoo.tests.common import TransactionCase


class TestDomainIsolation(TransactionCase):

    def test_commission_does_not_write_transaction_state(self):
        commission_model = self.env["plasticos.commission.rule"]
        methods = dir(commission_model)
        forbidden = [m for m in methods if "state" in m]
        self.assertFalse(forbidden)
