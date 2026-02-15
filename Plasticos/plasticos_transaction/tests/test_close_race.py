from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestCloseRace(TransactionCase):

    def test_double_close_attempt(self):
        tx = self.env["plasticos.transaction"].create({})
        tx.action_activate()
        tx.action_close()
        with self.assertRaises(UserError):
            tx.action_close()
