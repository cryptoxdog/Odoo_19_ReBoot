from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestComplianceFailure(TransactionCase):

    def test_close_blocked_on_compliance_fail(self):
        tx = self.env["plasticos.transaction"].create({})
        tx.action_activate()
        with self.assertRaises(Exception):
            tx.action_close()
