from odoo import models, fields


class LindaLoad(models.Model):
    _inherit = "linda.load"

    transaction_id = fields.Many2one("plasticos.transaction")

    def write(self, vals):
        res = super().write(vals)

        if "state" in vals and vals["state"] == "closed":
            for rec in self:
                if rec.transaction_id:
                    rec.transaction_id.message_post(
                        body="Logistics closed."
                    )

        return res
