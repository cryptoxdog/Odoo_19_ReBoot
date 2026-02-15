from odoo import models, fields, api


class L9KPI(models.Model):
    _name = "l9.kpi"
    _description = "L9 KPI Metrics"
    _auto = False

    total_intakes = fields.Integer()
    matched_intakes = fields.Integer()
    rejected_intakes = fields.Integer()
    avg_match_score = fields.Float()

    @api.model
    def compute_kpis(self):
        Intake = self.env["plasticos.intake"]

        total = Intake.search_count([])
        matched = Intake.search_count([("match_status", "=", "matched")])
        rejected = Intake.search_count([("match_status", "=", "rejected")])

        scores = []
        records = Intake.search([("match_response", "!=", False)])
        for r in records:
            ranked = r.match_response.get("ranked_buyers", [])
            if ranked:
                scores.append(ranked[0].get("score", 0))

        avg_score = sum(scores) / len(scores) if scores else 0

        return {
            "total_intakes": total,
            "matched_intakes": matched,
            "rejected_intakes": rejected,
            "avg_match_score": avg_score,
        }
