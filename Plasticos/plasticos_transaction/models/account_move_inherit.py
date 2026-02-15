from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        res = super().action_post()

        for rec in self:
            if rec.invoice_origin:
                so = self.env["sale.order"].search([("name", "=", rec.invoice_origin)], limit=1)
                if so and so.transaction_id:
                    tx = so.transaction_id

                    if rec.move_type == "out_invoice":
                        tx.customer_invoice_id = rec.id

                    if rec.move_type == "in_invoice":
                        tx.vendor_bill_ids = [(4, rec.id)]

