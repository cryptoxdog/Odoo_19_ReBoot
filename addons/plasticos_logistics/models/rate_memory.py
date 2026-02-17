from odoo import models, fields


class PlasticosRateMemory(models.Model):
    _name = "plasticos.rate.memory"
    _description = "Plasticos Rate Memory"

    carrier_id = fields.Many2one("res.partner", required=True)
    lane_key = fields.Char(required=True, index=True)
    rate_amount = fields.Float(required=True)
    rate_date = fields.Date(required=True)
