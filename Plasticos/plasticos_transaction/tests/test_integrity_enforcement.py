from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestIntegrity(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner = self.env.ref("base.res_partner_1")

    def _create_closed_transaction(self):
        tx = self.env["plasticos.transaction"].create({})
        invoice = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner.id,
            "invoice_line_ids": [(0, 0, {
                "name": "Revenue",
                "quantity": 1,
                "price_unit": 1000,
            })],
        })
        invoice.action_post()
        tx.customer_invoice_id = invoice.id

        bill = self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": self.partner.id,
            "invoice_line_ids": [(0, 0, {
                "name": "Cost",
                "quantity": 1,
                "price_unit": 400,
            })],
        })
        bill.action_post()
        tx.vendor_bill_ids = [(4, bill.id)]

        tx.action_activate()
        tx.action_close()
        return tx

    def test_cannot_mutate_closed(self):
        tx = self._create_closed_transaction()
        with self.assertRaises(UserError):
            tx.write({"commission_rule_id": False})

    def test_cannot_reassign_invoice(self):
        tx = self._create_closed_transaction()
        new_invoice = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner.id,
        })
        with self.assertRaises(UserError):
            tx.write({"customer_invoice_id": new_invoice.id})

    def test_negative_margin_block(self):
        tx = self.env["plasticos.transaction"].create({})
        invoice = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner.id,
            "invoice_line_ids": [(0, 0, {
                "name": "Revenue",
                "quantity": 1,
                "price_unit": 100,
            })],
        })
        invoice.action_post()
        tx.customer_invoice_id = invoice.id

        bill = self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": self.partner.id,
            "invoice_line_ids": [(0, 0, {
                "name": "Cost",
                "quantity": 1,
                "price_unit": 200,
            })],
        })
        bill.action_post()
        tx.vendor_bill_ids = [(4, bill.id)]

        tx.action_activate()
        with self.assertRaises(UserError):
            tx.action_close()
