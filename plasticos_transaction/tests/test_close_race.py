from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestCloseRace(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test partner
        cls.partner = cls.env["res.partner"].create({
            "name": "Test Partner Close Race",
        })
        # Create and add user to manager group
        cls.manager_group = cls.env.ref("plasticos_transaction.group_plasticos_manager")
        cls.env.user.groups_id = [(4, cls.manager_group.id)]

    def _create_posted_invoice(self):
        """Create a posted customer invoice for testing."""
        invoice = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner.id,
            "invoice_line_ids": [(0, 0, {
                "name": "Test Product",
                "quantity": 1,
                "price_unit": 100.0,
            })],
        })
        invoice.action_post()
        return invoice

    def test_double_close_attempt(self):
        """Test that closing an already-closed transaction raises UserError."""
        invoice = self._create_posted_invoice()
        tx = self.env["plasticos.transaction"].create({
            "customer_invoice_id": invoice.id,
        })
        tx.action_activate()
        tx.action_close()
        with self.assertRaises(UserError):
            tx.action_close()
