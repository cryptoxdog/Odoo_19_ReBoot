from odoo import models, fields, api
from odoo.exceptions import UserError


class PlasticosTransaction(models.Model):
    _name = "plasticos.transaction"
    _description = "Plasticos Transaction"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True, copy=False, default="New")

    sale_order_id = fields.Many2one("sale.order")
    purchase_order_ids = fields.Many2many("purchase.order")

    linda_load_id = fields.Many2one("linda.load")

    customer_invoice_id = fields.Many2one(
        "account.move",
        domain=[("move_type", "=", "out_invoice")]
    )

    vendor_bill_ids = fields.Many2many(
        "account.move",
        relation="plasticos_tx_vendor_rel",
        domain=[("move_type", "=", "in_invoice")]
    )

    freight_bill_ids = fields.Many2many(
        "account.move",
        relation="plasticos_tx_freight_rel",
        domain=[("move_type", "=", "in_invoice")]
    )

    revenue_total = fields.Float(compute="_compute_financials", store=True)
    cost_total = fields.Float(compute="_compute_financials", store=True)
    gross_margin = fields.Float(compute="_compute_financials", store=True)
    net_margin = fields.Float(compute="_compute_financials", store=True)

    commission_rule_id = fields.Many2one("plasticos.commission.rule")
    commission_amount = fields.Float(compute="_compute_commission", store=True)
    commission_locked = fields.Boolean(default=False)

    compliance_status = fields.Selection(
        [("compliant", "Compliant"), ("missing", "Missing Docs")],
        compute="_compute_compliance",
        store=True
    )

    state = fields.Selection([
        ("draft", "Draft"),
        ("active", "Active"),
        ("closed", "Closed")
    ], default="draft", tracking=True)

    @api.depends(
        "customer_invoice_id.amount_total",
        "vendor_bill_ids.amount_total",
        "freight_bill_ids.amount_total"
    )
    def _compute_financials(self):
        for rec in self:
            revenue = rec.customer_invoice_id.amount_total if rec.customer_invoice_id else 0.0
            vendor_cost = sum(rec.vendor_bill_ids.mapped("amount_total"))
            freight_cost = sum(rec.freight_bill_ids.mapped("amount_total"))
            cost = vendor_cost + freight_cost
            rec.revenue_total = revenue
            rec.cost_total = cost
            rec.gross_margin = revenue - cost
            rec.net_margin = revenue - cost

    @api.depends("gross_margin", "commission_rule_id", "state")
    def _compute_commission(self):
        service = self.env["plasticos.commission.service"]
        for rec in self:
            if rec.commission_locked:
                continue
            rec.commission_amount = service.compute_commission(rec)

    @api.depends("id")
    def _compute_compliance(self):
        service = self.env["plasticos.compliance.service"]
        for rec in self:
            if service.is_compliant("plasticos.transaction", rec.id):
                rec.compliance_status = "compliant"
            else:
                rec.compliance_status = "missing"

    def action_activate(self):
        self.state = "active"

    def action_close(self):
        service_docs = self.env["plasticos.compliance.service"]
        service_commission = self.env["plasticos.commission.service"]

        for rec in self:
            if rec.customer_invoice_id.state != "posted":
                raise UserError("Customer invoice must be posted.")

            if any(bill.state != "posted" for bill in rec.vendor_bill_ids):
                raise UserError("Vendor bills must be posted.")

            if rec.linda_load_id and rec.linda_load_id.state != "closed":
                raise UserError("Logistics must be closed.")

            if not service_docs.is_compliant("plasticos.transaction", rec.id):
                raise UserError("Required documents missing.")

            rec.commission_amount = service_commission.compute_commission(rec)
            rec.commission_locked = True
            rec.state = "closed"
