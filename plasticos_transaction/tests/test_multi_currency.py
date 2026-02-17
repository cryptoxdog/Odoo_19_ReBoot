from odoo.tests.common import TransactionCase


class TestMultiCurrency(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test partner (don't rely on demo data)
        cls.partner = cls.env["res.partner"].create({
            "name": "Test Partner Multi Currency",
        })

    def test_margin_computation_multi_currency(self):
        """Test that margin computation works with non-default currency."""
        currency = self.env.ref("base.EUR")

        invoice = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner.id,
            "currency_id": currency.id,
            "invoice_line_ids": [(0, 0, {
                "name": "Test Product EUR",
                "quantity": 1,
                "price_unit": 500.0,
            })],
        })

        tx = self.env["plasticos.transaction"].create({
            "customer_invoice_id": invoice.id,
        })

        self.assertIsNotNone(tx.gross_margin)
        self.assertEqual(tx.revenue_total, 500.0)
