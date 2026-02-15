from odoo import http
from odoo.http import request
import time

class L9MetricsController(http.Controller):

    @http.route("/metrics", type="http", auth="none")
    def metrics(self):
        TraceRun = request.env["l9.trace.run"].sudo()

        total = TraceRun.search_count([])
        errors = TraceRun.search_count([("outcome", "=", "error")])
        ok = TraceRun.search_count([("outcome", "=", "ok")])

        latencies = []
        runs = TraceRun.search([("start_ts", "!=", False), ("end_ts", "!=", False)])
        for r in runs:
            delta = (r.end_ts - r.start_ts).total_seconds()
            latencies.append(delta)

        buckets = [0.5, 1, 2, 3, 5]
        bucket_counts = {b: 0 for b in buckets}

        for l in latencies:
            for b in buckets:
                if l <= b:
                    bucket_counts[b] += 1

        output = []
        output.append(f"trace_runs_total {total}")
        output.append(f"trace_runs_ok_total {ok}")
        output.append(f"trace_runs_error_total {errors}")

        for b in buckets:
            output.append(f'l9_latency_bucket{{le="{b}"}} {bucket_counts[b]}')

        return request.make_response(
            "\n".join(output),
            headers=[("Content-Type", "text/plain")]
        )
4️⃣ Match-Quality Regression Detection
New module:

Plasticos/
└── l9_regression/
