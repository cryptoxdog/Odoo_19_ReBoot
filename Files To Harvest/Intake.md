## FILE TREE

```
Plasticos/
└── plasticos_intake/
    ├── __manifest__.py
    ├── __init__.py
    ├── models/
    │   ├── __init__.py
    │   └── intake.py
    ├── security/
    │   └── ir.model.access.csv
    └── views/
        └── intake_views.xml
```

---

## FILE: `Plasticos/plasticos_intake/__manifest__.py`

```python
{
    "name": "PlasticOS Intake",
    "version": "1.0.0",
    "summary": "Transactional Material Intake Engine",
    "author": "PlasticOS",
    "depends": [
        "base",
        "mail",
        "plasticos_material",
        "plasticos_processing"
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/intake_views.xml"
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3"
}
```

---

## FILE: `Plasticos/plasticos_intake/__init__.py`

```python
from . import models
```

---

## FILE: `Plasticos/plasticos_intake/models/__init__.py`

```python
from . import intake
```

---

## FILE: `Plasticos/plasticos_intake/models/intake.py`

```python
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
```

---

## FILE: `Plasticos/plasticos_intake/security/ir.model.access.csv`

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_plasticos_intake_user,plasticos.intake.user,model_plasticos_intake,base.group_user,1,1,1,0
access_plasticos_intake_manager,plasticos.intake.manager,model_plasticos_intake,base.group_system,1,1,1,1
```

---

## FILE: `Plasticos/plasticos_intake/views/intake_views.xml`

```xml
<odoo>

    <record id="view_plasticos_intake_tree" model="ir.ui.view">
        <field name="name">plasticos.intake.tree</field>
        <field name="model">plasticos.intake</field>
        <field name="arch" type="xml">
            <tree>
                <field name="name"/>
                <field name="partner_id"/>
                <field name="polymer"/>
                <field name="form"/>
                <field name="quantity_per_load_lbs"/>
                <field name="deal_type"/>
                <field name="match_status"/>
            </tree>
        </field>
    </record>

    <record id="view_plasticos_intake_form" model="ir.ui.view">
        <field name="name">plasticos.intake.form</field>
        <field name="model">plasticos.intake</field>
        <field name="arch" type="xml">
            <form>
                <sheet>

                    <group string="Identity">
                        <field name="name"/>
                        <field name="partner_id"/>
                        <field name="facility_id"/>
                        <field name="processing_profile_id"/>
                    </group>

                    <group string="Raw Description">
                        <field name="material_hint_text"/>
                    </group>

                    <group string="Material Snapshot">
                        <field name="polymer"/>
                        <field name="form"/>
                        <field name="color"/>
                        <field name="source_type"/>
                        <field name="grade_hint"/>
                    </group>

                    <group string="Observed Quality">
                        <field name="mfi_value"/>
                        <field name="density_value"/>
                        <field name="moisture_ppm"/>
                        <field name="contamination_total_pct"/>
                        <field name="has_metal"/>
                        <field name="has_fr"/>
                        <field name="has_residue"/>
                        <field name="filler_type"/>
                        <field name="filler_pct"/>
                        <field name="contamination_notes"/>
                    </group>

                    <group string="Origin">
                        <field name="origin_application"/>
                        <field name="origin_sector"/>
                        <field name="origin_process_type"/>
                    </group>

                    <group string="Commercial">
                        <field name="quantity_per_load_lbs"/>
                        <field name="loads_per_month"/>
                        <field name="deal_type"/>
                        <field name="contract_duration_months"/>
                    </group>

                    <group string="Matching">
                        <field name="match_status"/>
                        <field name="match_response"/>
                    </group>

                </sheet>
            </form>
        </field>
    </record>

    <record id="action_plasticos_intake" model="ir.actions.act_window">
        <field name="name">Intake</field>
        <field name="res_model">plasticos.intake</field>
        <field name="view_mode">tree,form</field>
    </record>

</odoo>
```