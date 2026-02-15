from odoo import models, fields, api
from odoo.exceptions import UserError


class PlasticosTransaction(models.Model):
    _name = "plasticos.transaction"
    _description = "Plasticos Deal Transaction"
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
        relation="plasticos_transaction_vendor_bill_rel",
        domain=[("move_type", "=", "in_invoice")]
    )

    freight_bill_ids = fields.Many2many(
        "account.move",
        relation="plasticos_transaction_freight_bill_rel",
        domain=[("move_type", "=", "in_invoice")]
    )

    sales_rep_id = fields.Many2one("res.users")
    commission_rule_id = fields.Many2one("plasticos.commission.rule")

    commission_override_flat = fields.Float()

    revenue_total = fields.Float(compute="_compute_financials", store=True)
    cost_total = fields.Float(compute="_compute_financials", store=True)
    gross_margin = fields.Float(compute="_compute_financials", store=True)
    commission_amount = fields.Float(compute="_compute_financials", store=True)
    net_margin = fields.Float(compute="_compute_financials", store=True)

    state = fields.Selection([
        ("draft", "Draft"),
        ("active", "Active"),
        ("closed", "Closed")
    ], default="draft", tracking=True)

    @api.depends(
        "customer_invoice_id.amount_total",
        "vendor_bill_ids.amount_total",
        "freight_bill_ids.amount_total",
        "commission_rule_id.percentage",
        "commission_override_flat"
    )
    def _compute_financials(self):
        for rec in self:
            revenue = rec.customer_invoice_id.amount_total if rec.customer_invoice_id else 0.0

            vendor_cost = sum(rec.vendor_bill_ids.mapped("amount_total"))
            freight_cost = sum(rec.freight_bill_ids.mapped("amount_total"))

            cost = vendor_cost + freight_cost
            gross = revenue - cost

            if rec.commission_override_flat:
                commission = rec.commission_override_flat
            elif rec.commission_rule_id:
                commission = gross * rec.commission_rule_id.percentage
            else:
                commission = 0.0

            net = gross - commission

            rec.revenue_total = revenue
            rec.cost_total = cost
            rec.gross_margin = gross
            rec.commission_amount = commission
            rec.net_margin = net

    def action_activate(self):
        self.state = "active"

    def action_close(self):
        for rec in self:
            if not rec.customer_invoice_id or rec.customer_invoice_id.state != "posted":
                raise UserError("Customer invoice must be posted.")

            if any(bill.state != "posted" for bill in rec.vendor_bill_ids):
                raise UserError("All vendor bills must be posted.")

            if rec.linda_load_id and rec.linda_load_id.state != "closed":
                raise UserError("Logistics must be closed.")

            rec.state = "closed"
🔐 SECURITY
