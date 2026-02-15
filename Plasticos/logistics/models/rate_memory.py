from odoo import models, fields


class LindaRateMemory(models.Model):
    _name = "linda.rate.memory"
    _description = "Linda Rate Memory"

    carrier_id = fields.Many2one("res.partner", required=True)
    lane_key = fields.Char(required=True, index=True)
    rate_amount = fields.Float(required=True)
    rate_date = fields.Date(required=True)
