from odoo import models, fields


class L9ShadowLog(models.Model):
    _name = "l9.shadow.log"
    _description = "L9 Shadow Score Comparison"

    intake_id = fields.Many2one("plasticos.intake")
    primary_score = fields.Float()
    shadow_score = fields.Float()
    delta = fields.Float()
