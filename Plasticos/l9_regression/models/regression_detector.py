from odoo import models, fields, api

class L9RegressionLog(models.Model):
    _name = "l9.regression.log"
    _description = "L9 Match Regression Log"

    intake_id = fields.Many2one("plasticos.intake")
    previous_score = fields.Float()
    current_score = fields.Float()
    regression_detected = fields.Boolean()


class L9RegressionDetector(models.AbstractModel):
    _name = "l9.regression.detector"

    def run_regression_check(self):
        Intake = self.env["plasticos.intake"].search([
            ("match_response", "!=", False)
        ])

        for r in Intake:
            ranked = r.match_response.get("ranked_buyers", [])
            if not ranked:
                continue

            current_score = ranked[0].get("score", 0)

            if hasattr(r, "previous_score") and r.previous_score:
                if current_score < r.previous_score - 0.15:
                    self.env["l9.regression.log"].create({
                        "intake_id": r.id,
                        "previous_score": r.previous_score,
                        "current_score": current_score,
                        "regression_detected": True,
                    })

            r.previous_score = current_score
