from odoo import models, fields, api
from odoo.exceptions import UserError


class PlasticosTransaction(models.Model):
    _name = "plasticos.transaction"
    _description = "Plasticos Deal Transaction"
    _inherit = ["mail.thread"]

    _sql_constraints = [
        (
            "unique_transaction_name",
            "unique(name)",
            "Transaction reference must be unique."
        ),
        (
            "unique_customer_invoice_link",
            "unique(customer_invoice_id)",
            "Customer invoice is already linked to another transaction."
        ),
        (
            "non_negative_margin_on_close",
            "CHECK(state != 'closed' OR gross_margin >= 0)",
            "Closed transactions cannot have negative gross margin."
        ),
    ]

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

    commission_frozen = fields.Boolean(default=False, copy=False)
    commission_frozen_amount = fields.Float(copy=False)
    commission_frozen_at = fields.Datetime(copy=False)

    state = fields.Selection([
        ("draft", "Draft"),
        ("active", "Active"),
        ("closed", "Closed")
    ], default="draft", tracking=True)

    def init(self):
        self._cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            plasticos_vendor_bill_unique
            ON plasticos_transaction_vendor_bill_rel (account_move_id);
        """)

        self._cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            plasticos_freight_bill_unique
            ON plasticos_transaction_freight_bill_rel (account_move_id);
        """)

        self._cr.execute("""
            CREATE INDEX IF NOT EXISTS plasticos_tx_state_idx
            ON plasticos_transaction (state);
        """)

        self._cr.execute("""
            CREATE INDEX IF NOT EXISTS plasticos_tx_sale_idx
            ON plasticos_transaction (sale_order_id);
        """)

        self._cr.execute("""
            CREATE INDEX IF NOT EXISTS plasticos_tx_invoice_idx
            ON plasticos_transaction (customer_invoice_id);
        """)

        self._cr.execute("""
            CREATE INDEX IF NOT EXISTS plasticos_tx_commission_frozen_idx
            ON plasticos_transaction (commission_frozen);
        """)

        self._cr.execute("""
            CREATE INDEX IF NOT EXISTS plasticos_tx_margin_idx
            ON plasticos_transaction (gross_margin);
        """)

    @api.model
    def create(self, vals):
        if vals.get("name", "New") == "New":
            vals["name"] = self.env["ir.sequence"].next_by_code(
                "plasticos.transaction"
            ) or "New"
        return super().create(vals)

    def write(self, vals):
        for rec in self:
            # Block direct state mutation
            if "state" in vals:
                raise UserError("State can only be changed via action methods.")

            # Immutable identity
            if "name" in vals:
                raise UserError("Transaction reference cannot be modified.")

            # Closed transaction lock
            if rec.state == "closed":
                protected_fields = {
                    "sale_order_id",
                    "purchase_order_ids",
                    "customer_invoice_id",
                    "vendor_bill_ids",
                    "freight_bill_ids",
                    "commission_rule_id",
                    "commission_override_flat",
                }
                if protected_fields.intersection(vals.keys()):
                    raise UserError("Closed transactions are immutable.")

            # Commission override frozen guard
            if rec.commission_frozen and "commission_override_flat" in vals:
                raise UserError("Commission override cannot be modified after freeze.")

            # Customer invoice reassignment guard
            if rec.customer_invoice_id and "customer_invoice_id" in vals:
                raise UserError("Customer invoice cannot be reassigned once set.")

            # Vendor bill duplicate guard
            if "vendor_bill_ids" in vals:
                for bill in self.env["account.move"].browse(vals.get("vendor_bill_ids", [])):
                    existing = self.search([
                        ("vendor_bill_ids", "in", bill.id),
                        ("id", "!=", rec.id),
                    ])
                    if existing:
                        raise UserError("Vendor bill already linked to another transaction.")

            # Freight bill duplicate guard
            if "freight_bill_ids" in vals:
                for bill in self.env["account.move"].browse(vals.get("freight_bill_ids", [])):
                    existing = self.search([
                        ("freight_bill_ids", "in", bill.id),
                        ("id", "!=", rec.id),
                    ])
                    if existing:
                        raise UserError("Freight bill already linked to another transaction.")

        return super().write(vals)

    def unlink(self):
        for rec in self:
            if rec.state == "closed":
                raise UserError("Closed transactions cannot be deleted.")
        return super().unlink()

    @api.depends(
        "customer_invoice_id.amount_total",
        "vendor_bill_ids.amount_total",
        "freight_bill_ids.amount_total",
        "commission_rule_id.percentage",
        "commission_override_flat",
        "commission_frozen",
        "commission_frozen_amount"
    )
    def _compute_financials(self):
        for rec in self:
            revenue = rec.customer_invoice_id.amount_total if rec.customer_invoice_id else 0.0

            vendor_cost = sum(rec.vendor_bill_ids.mapped("amount_total"))
            freight_cost = sum(rec.freight_bill_ids.mapped("amount_total"))

            cost = vendor_cost + freight_cost
            gross = revenue - cost

            if rec.commission_frozen:
                commission = rec.commission_frozen_amount
            else:
                if rec.commission_override_flat is not False and rec.commission_override_flat is not None:
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

            # Compliance Gate
            compliance_service = self.env["plasticos.document"].sudo()
            if hasattr(compliance_service, "check_transaction_compliance"):
                compliance_service.check_transaction_compliance(rec)

            # Prevent negative margin close
            if rec.gross_margin < 0:
                raise UserError("Cannot close transaction with negative gross margin.")

            # Freeze commission
            rec.commission_frozen = True
            rec.commission_frozen_amount = rec.commission_amount
            rec.commission_frozen_at = fields.Datetime.now()

            rec.state = "closed"
