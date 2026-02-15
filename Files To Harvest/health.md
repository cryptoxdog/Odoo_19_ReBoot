Plasticos/
└── l9_health/
FILE: __manifest__.py
{
    "name": "L9 Health Monitor",
    "version": "1.0.0",
    "depends": ["l9_trace", "plasticos_intake"],
    "data": [
        "views/health_dashboard.xml",
        "data/health_cron.xml",
    ],
    "installable": True,
}
FILE: models/health_metrics.py
from odoo import models, fields, api


class L9HealthMetrics(models.Model):
    _name = "l9.health.metrics"
    _description = "L9 Health Metrics"
    _auto = False

    total_runs = fields.Integer()
    error_runs = fields.Integer()
    avg_latency = fields.Float()

    @api.model
    def compute_metrics(self):
        TraceRun = self.env["l9.trace.run"]

        total = TraceRun.search_count([])
        errors = TraceRun.search_count([("outcome", "=", "error")])

        runs = TraceRun.search([])
        latencies = []
        for r in runs:
            if r.end_ts and r.start_ts:
                latencies.append((r.end_ts - r.start_ts).total_seconds())

        avg = sum(latencies) / len(latencies) if latencies else 0

        return {
            "total_runs": total,
            "error_runs": errors,
            "avg_latency": avg,
        }
FILE: views/health_dashboard.xml
<odoo>
    <record id="view_l9_health_dashboard" model="ir.ui.view">
        <field name="name">l9.health.dashboard</field>
        <field name="model">l9.health.metrics</field>
        <field name="arch" type="xml">
            <tree>
                <field name="total_runs"/>
                <field name="error_runs"/>
                <field name="avg_latency"/>
            </tree>
        </field>
    </record>
</odoo>
FILE: data/health_cron.xml
<odoo>
    <record id="cron_l9_health_monitor" model="ir.cron">
        <field name="name">L9 Health Monitor</field>
        <field name="model_id" ref="model_l9_health_metrics"/>
        <field name="state">code</field>
        <field name="code">model.compute_metrics()</field>
        <field name="interval_number">5</field>
        <field name="interval_type">minutes</field>
    </record>
</odoo>
C️⃣ DRIFT DETECTOR MODULE
New module:

Plasticos/
└── l9_drift/
FILE: __manifest__.py
{
    "name": "L9 Drift Detector",
    "version": "1.0.0",
    "depends": ["l9_trace"],
    "data": [
        "data/drift_cron.xml",
    ],
    "installable": True,
}
FILE: models/drift_detector.py
import hashlib
import json
from odoo import models, fields


class L9DriftLog(models.Model):
    _name = "l9.drift.log"
    _description = "L9 Drift Log"

    intake_id = fields.Many2one("plasticos.intake")
    previous_hash = fields.Char()
    current_hash = fields.Char()
    drift_detected = fields.Boolean()


class L9DriftDetector(models.AbstractModel):
    _name = "l9.drift.detector"

    def run_drift_check(self):
        Intakes = self.env["plasticos.intake"].search([])

        for intake in Intakes:
            if not intake.last_packet_payload:
                continue

            snapshot = json.dumps(
                intake.last_packet_payload.get("payload", {}),
                sort_keys=True
            ).encode()

            current_hash = hashlib.sha256(snapshot).hexdigest()

            if intake.last_payload_hash and intake.last_payload_hash != current_hash:
                self.env["l9.drift.log"].create({
                    "intake_id": intake.id,
                    "previous_hash": intake.last_payload_hash,
                    "current_hash": current_hash,
                    "drift_detected": True,
                })
FILE: data/drift_cron.xml
<odoo>
    <record id="cron_l9_drift_detector" model="ir.cron">
        <field name="name">L9 Drift Detector</field>
        <field name="model_id" ref="model_l9_drift_detector"/>
        <field name="state">code</field>
        <field name="code">model.run_drift_check()</field>
        <field name="interval_number">60</field>
        <field name="interval_type">minutes</field>
    </record>
</odoo>

