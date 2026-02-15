from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestSecurityPermissions(TransactionCase):

    def test_only_manager_can_close(self):
        tx = self.env["plasticos.transaction"].create({})
        user = self.env.ref("base.user_demo")
        with self.assertRaises(Exception):
            tx.with_user(user).action_close()
