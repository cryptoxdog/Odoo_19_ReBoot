from odoo import models, fields, api
from odoo.exceptions import ValidationError


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
        tracking=True
    )
    facility_id = fields.Many2one(
        "res.partner",
        domain="[('parent_id', '=', partner_id)]"
    )
    processing_profile_id = fields.Many2one(
        "plasticos.processing.profile"
    )

    # =========================
    # Raw Broker Layer
    # =========================

    material_hint_text = fields.Text(
        help="Raw broker description. Parsed later by L9."
    )

    # =========================
    # Material Snapshot (Schema-Aligned)
    # =========================

    polymer = fields.Char(required=True)
    form = fields.Char(required=True)
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
        ("matched", "Matched"),
        ("rejected", "Rejected"),
        ("error", "Error")
    ], default="pending", tracking=True)

    match_response = fields.Json()

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
