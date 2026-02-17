from odoo.tests.common import TransactionCase


class TestMultiCurrency(TransactionCase):

    def test_margin_computation_multi_currency(self):
        currency = self.env.ref("base.EUR")
        partner = self.env.ref("base.res_partner_1")

        invoice = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "currency_id": currency.id,
        })

        tx = self.env["plasticos.transaction"].create({
            "customer_invoice_id": invoice.id,
        })

        self.assertIsNotNone(tx.gross_margin)
