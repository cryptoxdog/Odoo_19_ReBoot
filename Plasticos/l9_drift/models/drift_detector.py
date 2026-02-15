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
