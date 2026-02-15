Plasticos/
└── l9_canary/
Plasticos/l9_canary/manifest.py
{
    "name": "L9 Canary Gate",
    "version": "1.0.0",
    "depends": ["plasticos_intake", "l9_adapter"],
    "data": [],
    "installable": True,
}
Plasticos/l9_canary/init.py
from . import models
Plasticos/l9_canary/models/init.py
from . import canary_gate
Plasticos/l9_canary/models/canary_gate.py
from odoo import models, fields
import random


class L9CanaryConfig(models.Model):
    _name = "l9.canary.config"
    _description = "L9 Canary Configuration"

    enabled = fields.Boolean(default=False)
    canary_percentage = fields.Integer(default=10)
    canary_endpoint = fields.Char()


class L9CanaryGate(models.AbstractModel):
    _name = "l9.canary.gate"

    def should_use_canary(self):
        config = self.env["l9.canary.config"].search([], limit=1)
        if not config or not config.enabled:
            return False

        roll = random.randint(1, 100)
        return roll <= config.canary_percentage

    def resolve_endpoint(self, default_endpoint):
        config = self.env["l9.canary.config"].search([], limit=1)
        if self.should_use_canary() and config.canary_endpoint:
            return config.canary_endpoint
        return default_endpoint
Modify adapter endpoint resolution to use this gate.

2️⃣ Shadow Scoring (Dual Model Compare)
New module:

Plasticos/
└── l9_shadow/
Plasticos/l9_shadow/manifest.py
{
    "name": "L9 Shadow Scoring",
    "version": "1.0.0",
    "depends": ["plasticos_intake"],
    "data": [],
    "installable": True,
}
Plasticos/l9_shadow/init.py
from . import models
Plasticos/l9_shadow/models/init.py
from . import shadow_log
Plasticos/l9_shadow/models/shadow_log.py
from odoo import models, fields


class L9ShadowLog(models.Model):
    _name = "l9.shadow.log"
    _description = "L9 Shadow Score Comparison"

    intake_id = fields.Many2one("plasticos.intake")
    primary_score = fields.Float()
    shadow_score = fields.Float()
    delta = fields.Float()
Add to adapter after main response:

shadow_response = post_json(shadow_endpoint, packet, api_key, timeout)
shadow_score = shadow_response.get("ranked_buyers", [{}])[0].get("score", 0)
primary_score = resp.get("ranked_buyers", [{}])[0].get("score", 0)

self.env["l9.shadow.log"].create({
    "intake_id": intake.id,
    "primary_score": primary_score,
    "shadow_score": shadow_score,
    "delta": shadow_score - primary_score,
})
3️⃣ Automatic Rollback Trigger
New module:

Plasticos/
└── l9_rollback/
Plasticos/l9_rollback/manifest.py
{
    "name": "L9 Automatic Rollback",
    "version": "1.0.0",
    "depends": ["l9_regression", "l9_canary"],
    "data": [
        "data/rollback_cron.xml"
    ],
    "installable": True,
}
Plasticos/l9_rollback/init.py
from . import models
Plasticos/l9_rollback/models/init.py
from . import rollback_controller
Plasticos/l9_rollback/models/rollback_controller.py
from odoo import models


class L9RollbackController(models.AbstractModel):
    _name = "l9.rollback.controller"

    def run_rollback_check(self):
        logs = self.env["l9.regression.log"].search([
            ("regression_detected", "=", True)
        ])

        if len(logs) > 5:
            config = self.env["l9.canary.config"].search([], limit=1)
            if config:
                config.enabled = False
Plasticos/l9_rollback/data/rollback_cron.xml
<odoo>
    <record id="cron_l9_rollback" model="ir.cron">
        <field name="name">L9 Auto Rollback</field>
        <field name="model_id" ref="model_l9_rollback_controller"/>
        <field name="state">code</field>
        <field name="code">model.run_rollback_check()</field>
        <field name="interval_number">5</field>
        <field name="interval_type">minutes</field>
    </record>
</odoo>
4️⃣ Linda Dispatch Hardening
New module:

Plasticos/
└── linda_dispatch/
Plasticos/linda_dispatch/manifest.py
{
    "name": "Linda Dispatch Engine",
    "version": "1.0.0",
    "depends": ["stock", "l9_trace"],
    "data": [
        "views/dispatch_views.xml"
    ],
    "installable": True,
}
Plasticos/linda_dispatch/models/dispatch.py
from odoo import models, fields
from odoo.addons.l9_trace.services.trace_kernel import TraceKernel
from odoo.addons.l9_trace.services.correlation import new_correlation_id


class LindaDispatch(models.Model):
    _name = "linda.dispatch"
    _description = "Linda Dispatch"

    name = fields.Char(required=True)
    state = fields.Selection([
        ("quoted", "Quoted"),
        ("dispatched", "Dispatched"),
        ("picked_up", "Picked Up"),
        ("delivered", "Delivered"),
        ("closed", "Closed"),
    ], default="quoted")

    def action_transition(self, new_state):
        for rec in self:
            correlation_id = new_correlation_id()
            trace = TraceKernel(self.env, service_name="linda_dispatch", correlation_id=correlation_id)
            span = trace.start_span("state_transition", "system")
            rec.state = new_state
            trace.event(span, "dispatch_state_changed", {
                "dispatch_id": rec.id,
                "new_state": new_state
            })
            trace.finalize("ok")