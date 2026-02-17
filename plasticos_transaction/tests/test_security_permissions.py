from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestSecurityPermissions(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test partner
        cls.partner = cls.env["res.partner"].create({
            "name": "Test Partner Security",
        })
        # Create a non-manager user for testing
        cls.non_manager_user = cls.env["res.users"].create({
            "name": "Test Non-Manager User",
            "login": "test_non_manager_plasticos",
            "email": "nonmanager@test.plasticos.com",
            "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
        })

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

    def test_only_manager_can_close(self):
        """Test that non-manager users cannot close transactions."""
        invoice = self._create_posted_invoice()
        tx = self.env["plasticos.transaction"].create({
            "customer_invoice_id": invoice.id,
        })
        tx.action_activate()

        # Attempt to close as non-manager should fail
        with self.assertRaises(UserError):
            tx.with_user(self.non_manager_user).action_close()
