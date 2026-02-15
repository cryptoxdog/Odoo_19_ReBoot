from odoo import models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        service = self.env["plasticos.compliance.service"]
        res = super().action_post()

        for rec in self:
            if rec.move_type == "out_invoice" and rec.invoice_origin:
                so = self.env["sale.order"].search([("name", "=", rec.invoice_origin)], limit=1)
                if so and so.transaction_id:
                    tx = so.transaction_id

                    if not service.is_compliant("plasticos.transaction", tx.id):
                        raise UserError("Missing required documents for invoice posting.")

                    tx.customer_invoice_id = rec.id

            if rec.move_type == "in_invoice" and rec.invoice_origin:
                so = self.env["sale.order"].search([("name", "=", rec.invoice_origin)], limit=1)
                if so and so.transaction_id:
                    so.transaction_id.vendor_bill_ids = [(4, rec.id)]

        return res
