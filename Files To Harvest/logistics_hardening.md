
🔒 Hardening Pack v1
All modifications below are production-grade.

1️⃣ Enforce Lane Immutability After Rate Confirmation
Patch: Plasticos/logistics/models/load.py
Add override:

def write(self, vals):
    for rec in self:
        if rec.state in ["rate_confirmed", "scheduled", "dispatched", "picked_up", "delivered", "closed"]:
            if any(field in vals for field in ["origin_zip", "destination_zip"]):
                raise UserError("Lane cannot be modified after rate confirmation.")
    return super().write(vals)
2️⃣ Lock Editing After Dispatch
Extend write guard:

def write(self, vals):
    for rec in self:
        if rec.state in ["dispatched", "picked_up", "delivered", "closed"]:
            blocked_fields = set(vals.keys()) - {"bol_pickup_attached", "bol_delivery_attached"}
            if blocked_fields:
                raise UserError("Load locked after dispatch.")
    return super().write(vals)
Merge both guards cleanly in one write override.

3️⃣ Auto-Escalate if Stuck > X Hours
Add fields.

Add to load.py
entered_state_at = fields.Datetime(default=fields.Datetime.now, index=True)
Modify transition:

rec.state = new_state
rec.entered_state_at = fields.Datetime.now()
Create Escalation Service
Plasticos/logistics/services/escalation_engine.py
from odoo import fields

ESCALATION_HOURS = {
    "awaiting_ready": 48,
    "ready_confirmed": 24,
    "rate_confirmed": 24,
    "scheduled": 24,
    "dispatched": 72,
}


def check_escalations(env):
    now = fields.Datetime.now()

    loads = env["linda.load"].search([
        ("state", "in", list(ESCALATION_HOURS.keys()))
    ])

    for load in loads:
        limit = ESCALATION_HOURS.get(load.state)
        if not limit:
            continue

        delta = (now - load.entered_state_at).total_seconds() / 3600

        if delta > limit:
            load.message_post(body=f"SLA breach: stuck in {load.state} > {limit}h")
Add Cron
Plasticos/logistics/data/cron.xml
<record id="cron_escalation" model="ir.cron">
    <field name="name">Linda Escalation Monitor</field>
    <field name="model_id" ref="model_load"/>
    <field name="state">code</field>
    <field name="code">model.env['logistics.services.escalation_engine'].check_escalations(model.env)</field>
    <field name="interval_number">1</field>
    <field name="interval_type">hours</field>
</record>
4️⃣ SLA Breach Tracking Field
Add to load.py:

sla_breached = fields.Boolean(default=False, index=True)
Modify escalation:

if delta > limit:
    load.sla_breached = True
5️⃣ Cycle-Time Performance Analytics
Add timestamps:

dispatched_at = fields.Datetime()
delivered_at = fields.Datetime()
Update transitions:

if new_state == "dispatched":
    rec.dispatched_at = fields.Datetime.now()

if new_state == "delivered":
    rec.delivered_at = fields.Datetime.now()
Add Computed Field
cycle_time_hours = fields.Float(compute="_compute_cycle_time", store=True)

def _compute_cycle_time(self):
    for rec in self:
        if rec.dispatched_at and rec.delivered_at:
            delta = (rec.delivered_at - rec.dispatched_at).total_seconds() / 3600
            rec.cycle_time_hours = delta
        else:
            rec.cycle_time_hours = 0
Add index:

cycle_time_hours = fields.Float(..., index=True)