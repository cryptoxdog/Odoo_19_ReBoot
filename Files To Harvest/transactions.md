Plasticos/
└── plasticos_transaction/
    ├── __manifest__.py
    ├── __init__.py
    ├── models/
    │   ├── __init__.py
    │   ├── transaction.py
    │   ├── sale_inherit.py
    │   ├── purchase_inherit.py
    │   ├── account_move_inherit.py
    │   └── inherit.py
    ├── security/
    │   └── ir.model.access.csv
    └── views/
        └── transaction_views.xml
Plasticos/plasticos_transaction/manifest.py
{
    "name": "Plasticos Transaction Spine",
    "version": "1.0.0",
    "depends": [
        "base",
        "mail",
        "account",
        "sale_management",
        "purchase",
        "logistics",
        "plasticos_documents",
        "plasticos_commission"
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/transaction_views.xml"
    ],
    "installable": True,
    "application": False,
}
Plasticos/plasticos_transaction/init.py
from . import models
Plasticos/plasticos_transaction/models/init.py
from . import transaction
from . import sale_inherit
from . import purchase_inherit
from . import account_move_inherit
from . import inherit
🧠 CORE TRANSACTION MODEL
Plasticos/plasticos_transaction/models/transaction.py
from odoo import models, fields, api
from odoo.exceptions import UserError


class PlasticosTransaction(models.Model):
    _name = "plasticos.transaction"
    _description = "Plasticos Transaction"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True, copy=False, default="New")

    sale_order_id = fields.Many2one("sale.order")
    purchase_order_ids = fields.Many2many("purchase.order")

    load_id = fields.Many2one("linda.load")

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
        service = self.env["plasticos.compliance.service"]

        for rec in self:
            if not rec.customer_invoice_id or rec.customer_invoice_id.state != "posted":
                raise UserError("Customer invoice must be posted.")

            if any(bill.state != "posted" for bill in rec.vendor_bill_ids):
                raise UserError("All vendor bills must be posted.")

            if rec.load_id and rec.load_id.state != "closed":
                raise UserError("Logistics must be closed.")

            if not service.is_compliant("plasticos.transaction", rec.id):
                raise UserError("Required documents missing.")

            rec.state = "closed"
🔄 SALE ORDER INTEGRATION
Plasticos/plasticos_transaction/models/sale_inherit.py
from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = "sale.order"

    transaction_id = fields.Many2one("plasticos.transaction")

    def action_confirm(self):
        res = super().action_confirm()

        for rec in self:
            if not rec.transaction_id:
                transaction = self.env["plasticos.transaction"].create({
                    "name": f"TX-{rec.name}",
                    "sale_order_id": rec.id
                })
                rec.transaction_id = transaction.id

        return res
🛒 PURCHASE ORDER LINKING
Plasticos/plasticos_transaction/models/purchase_inherit.py
from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_confirm(self):
        res = super().button_confirm()

        for rec in self:
            if rec.origin:
                so = self.env["sale.order"].search([("name", "=", rec.origin)], limit=1)
                if so and so.transaction_id:
                    so.transaction_id.purchase_order_ids = [(4, rec.id)]

        return res
💵 ACCOUNT MOVE LINKING
Plasticos/plasticos_transaction/models/account_move_inherit.py
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

        return res