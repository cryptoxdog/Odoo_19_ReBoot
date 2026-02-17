from odoo import models, fields


class PlasticosDocumentRule(models.Model):
    _name = "plasticos.document.rule"
    _description = "Document Compliance Rule"

    name = fields.Char(required=True)
    tag_id = fields.Many2one("plasticos.document.tag", required=True)
    res_model = fields.Char(required=True)
    client_id = fields.Many2one("res.partner")
    required_for_invoice = fields.Boolean(default=False)
    required_for_close = fields.Boolean(default=True)
    active = fields.Boolean(default=True)
