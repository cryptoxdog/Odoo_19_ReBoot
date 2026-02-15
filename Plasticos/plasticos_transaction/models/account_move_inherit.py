from odoo import models
from odoo.exceptions import UserError


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

            # Block credit note post-close drift
            if rec.move_type in ("out_refund", "in_refund"):
                tx = self.env["plasticos.transaction"].search([
                    "|",
                    ("customer_invoice_id", "=", rec.reversed_entry_id.id),
                    ("vendor_bill_ids", "in", rec.reversed_entry_id.id),
                ])
                if tx.filtered(lambda t: t.state == "closed"):
                    raise UserError("Cannot create credit note for closed transaction.")

        return res

    def unlink(self):
        for move in self:
            tx = self.env["plasticos.transaction"].search([
                "|",
                ("customer_invoice_id", "=", move.id),
                ("vendor_bill_ids", "in", move.id),
            ])
            if tx.filtered(lambda t: t.state == "closed"):
                raise UserError("Cannot delete invoice/bill linked to closed transaction.")
        return super().unlink()
