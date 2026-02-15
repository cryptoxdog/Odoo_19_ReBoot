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
