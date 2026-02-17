from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class PlasticosIntake(models.Model):
    _name = "plasticos.intake"
    _description = "PlasticOS Material Intake"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    # =========================
    # Identity
    # =========================

    name = fields.Char(required=True, tracking=True)
    partner_id = fields.Many2one(
        "res.partner",
        required=True,
        tracking=True,
        index=True,
    )
    facility_id = fields.Many2one(
        "res.partner",
        domain="[('parent_id', '=', partner_id)]"
    )
    # processing_profile_id = fields.Many2one(
    #     "plasticos.processing.profile"
    # )  # TODO: Enable when plasticos_processing module is available

    # =========================
    # Raw Broker Layer
    # =========================

    material_hint_text = fields.Text(
        help="Raw broker description. Parsed later by L9."
    )

    # =========================
    # Material Snapshot (Schema-Aligned)
    # =========================

    polymer = fields.Char(required=True, index=True)
    form = fields.Char(required=True, index=True)
    color = fields.Char()
    source_type = fields.Char()
    grade_hint = fields.Char()

    # =========================
    # Observed Quality (Instance-Level)
    # =========================

    mfi_value = fields.Float()
    density_value = fields.Float()
    moisture_ppm = fields.Integer()
    contamination_total_pct = fields.Float()

    has_metal = fields.Boolean()
    has_fr = fields.Boolean()
    has_residue = fields.Boolean()

    filler_type = fields.Char()
    filler_pct = fields.Float()

    contamination_notes = fields.Text()

    # =========================
    # Origin Intelligence
    # =========================

    origin_application = fields.Char()

    origin_sector = fields.Selection([
        ("medical", "Medical"),
        ("automotive", "Automotive"),
        ("packaging", "Packaging"),
        ("construction", "Construction"),
        ("consumer_goods", "Consumer Goods"),
        ("industrial", "Industrial"),
        ("other", "Other")
    ])

    origin_process_type = fields.Selection([
        ("injection", "Injection"),
        ("extrusion", "Extrusion"),
        ("blow_molding", "Blow Molding"),
        ("thermoforming", "Thermoforming"),
        ("rotomolding", "Rotomolding"),
        ("film", "Film"),
        ("compounding", "Compounding"),
        ("unknown", "Unknown")
    ], default="unknown")

    # =========================
    # Commercial Layer
    # =========================

    quantity_per_load_lbs = fields.Integer(required=True)
    loads_per_month = fields.Integer()

    deal_type = fields.Selection([
        ("spot", "Spot"),
        ("ongoing", "Ongoing")
    ], default="spot")

    contract_duration_months = fields.Integer()

    # =========================
    # Geo
    # =========================

    lat = fields.Float()
    lon = fields.Float()

    # =========================
    # Matching
    # =========================

    match_status = fields.Selection([
        ("pending", "Pending"),
        ("normalized", "Normalized"),
        ("matched", "Matched"),
        ("rejected", "Rejected"),
        ("error", "Error"),
    ], default="pending", tracking=True)

    match_response = fields.Json()

    normalized = fields.Boolean(
        default=False,
        help="Must be True before adapter emits packet",
    )

    last_packet_id = fields.Char(index=True)
    last_packet_version = fields.Char()
    last_packet_payload = fields.Json()
    last_packet_ts = fields.Datetime()

    # SQL Constraint (Odoo 19 syntax: named class attribute)
    _check_unique_packet = models.Constraint(
        "unique(last_packet_id, last_packet_version)",
        "Duplicate packet emission detected.",
    )

    # =========================
    # Validation
    # =========================

    @api.constrains("quantity_per_load_lbs")
    def _check_quantity(self):
        for rec in self:
            if rec.quantity_per_load_lbs <= 0:
                raise ValidationError("Quantity per load must be positive.")

    @api.constrains("loads_per_month")
    def _check_loads(self):
        for rec in self:
            if rec.loads_per_month and rec.loads_per_month < 0:
                raise ValidationError("Loads per month cannot be negative.")

    def action_mark_normalized(self):
        for rec in self:
            rec.write({
                "normalized": True,
                "match_status": "normalized",
            })

    def action_run_buyer_match(self):
        # TODO: Enable when l9_trace module is available
        # adapter = self.env["l9.adapter.service"]
        for rec in self:
            if not rec.normalized:
                raise UserError("Intake must be normalized before match.")
            # adapter.run_buyer_match(rec)
            raise UserError("L9 adapter not yet configured. Enable l9_trace module.")

    def action_replay_last_packet(self):
        # TODO: Enable when l9_trace module is available
        # adapter = self.env["l9.adapter.service"]
        for rec in self:
            if not rec.last_packet_payload:
                raise UserError("No stored packet to replay.")
            # adapter.emit_raw_packet(rec.last_packet_payload)
            raise UserError("L9 adapter not yet configured. Enable l9_trace module.")
