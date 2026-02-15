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

