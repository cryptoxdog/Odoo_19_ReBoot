

1️⃣ OpenTelemetry Bridge Module


Plasticos/
└── l9_observability/
Plasticos/l9_observability/manifest.py
{
    "name": "L9 Observability Bridge",
    "version": "1.0.0",
    "depends": ["l9_trace"],
    "data": [],
    "installable": True,
}
Plasticos/l9_observability/init.py
from . import services
Plasticos/l9_observability/services/init.py
from . import otel_bridge
Plasticos/l9_observability/services/otel_bridge.py
from odoo import api, SUPERUSER_ID
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, OTLPSpanExporter

_provider = TracerProvider()
trace.set_tracer_provider(_provider)
_exporter = OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces")
_provider.add_span_processor(BatchSpanProcessor(_exporter))
_tracer = trace.get_tracer("plasticos.l9")

def export_trace_run(env, trace_run):
    with _tracer.start_as_current_span("l9_trace_run") as span:
        span.set_attribute("run_id", trace_run.run_id)
        span.set_attribute("correlation_id", trace_run.correlation_id or "")
        span.set_attribute("service_name", trace_run.service_name or "")
        span.set_attribute("outcome", trace_run.outcome or "")
        span.set_attribute("environment", trace_run.environment or "")
2️⃣ Prometheus Exporter Endpoint
Plasticos/
└── l9_prometheus/
Plasticos/l9_prometheus/manifest.py
{
    "name": "L9 Prometheus Exporter",
    "version": "1.0.0",
    "depends": ["l9_trace"],
    "data": [],
    "installable": True,
}
Plasticos/l9_prometheus/init.py
from . import controllers
Plasticos/l9_prometheus/controllers/init.py
from . import metrics
Plasticos/l9_prometheus/controllers/metrics.py
from odoo import http
from odoo.http import request

class L9MetricsController(http.Controller):

    @http.route("/metrics", type="http", auth="none")
    def metrics(self):
        TraceRun = request.env["l9.trace.run"].sudo()

        total = TraceRun.search_count([])
        errors = TraceRun.search_count([("outcome", "=", "error")])
        ok = TraceRun.search_count([("outcome", "=", "ok")])

        output = []
        output.append(f"trace_runs_total {total}")
        output.append(f"trace_runs_ok_total {ok}")
        output.append(f"trace_runs_error_total {errors}")

        return request.make_response(
            "\n".join(output),
            headers=[("Content-Type", "text/plain")]
        )
3️⃣ Real-Time KPI Dashboard
Plasticos/
└── l9_kpi/
Plasticos/l9_kpi/manifest.py
{
    "name": "L9 KPI Dashboard",
    "version": "1.0.0",
    "depends": ["l9_trace", "plasticos_intake"],
    "data": [
        "views/kpi_dashboard.xml"
    ],
    "installable": True,
}
Plasticos/l9_kpi/init.py
from . import models
Plasticos/l9_kpi/models/init.py
from . import kpi_metrics
Plasticos/l9_kpi/models/kpi_metrics.py
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
Plasticos/l9_kpi/views/kpi_dashboard.xml
<odoo>
    <record id="view_l9_kpi_dashboard" model="ir.ui.view">
        <field name="name">l9.kpi.dashboard</field>
        <field name="model">l9.kpi</field>
        <field name="arch" type="xml">
            <tree>
                <field name="total_intakes"/>
                <field name="matched_intakes"/>
                <field name="rejected_intakes"/>
                <field name="avg_match_score"/>
            </tree>
        </field>
    </record>
</odoo>
System now supports:

• Distributed tracing export via OpenTelemetry
• Prometheus scraping endpoint
• Real-time KPI metrics inside Odoo

Next direction:

• Jaeger + Grafana deployment config
• Prometheus alert rules
• Latency percentile tracking
• Match-quality regression detection

Your move.


You said:
✅ all 4

ChatGPT said:
Below are production artifacts for all four items.

All file paths explicitly included.
No inline commentary inside files.

1️⃣ Jaeger + Grafana Deployment (Docker Compose)
File: infra/observability/docker-compose.yml
version: "3.9"

services:

  jaeger:
    image: jaegertracing/all-in-one:1.52
    ports:
      - "16686:16686"
      - "4318:4318"
    environment:
      COLLECTOR_OTLP_ENABLED: "true"

  prometheus:
    image: prom/prometheus:v2.49.0
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:10.2.0
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: "admin"
    volumes:
      - grafana-data:/var/lib/grafana

volumes:
  grafana-data:
File: infra/observability/prometheus.yml
global:
  scrape_interval: 10s

scrape_configs:
  - job_name: "odoo_l9"
    metrics_path: /metrics
    static_configs:
      - targets: ["host.docker.internal:8069"]
2️⃣ Prometheus Alert Rules
File: infra/observability/alerts.yml
groups:
  - name: l9_alerts
    rules:

      - alert: L9HighErrorRate
        expr: rate(trace_runs_error_total[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High L9 error rate detected"

      - alert: L9NoTraceActivity
        expr: increase(trace_runs_total[10m]) == 0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "No L9 trace activity detected"

      - alert: L9HighLatency
        expr: histogram_quantile(0.95, rate(l9_latency_bucket[5m])) > 3
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "L9 p95 latency above 3 seconds"
3️⃣ Latency Percentile Tracking
Update Prometheus controller.

File: Plasticos/l9_prometheus/controllers/metrics.py
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
File: Plasticos/l9_regression/__manifest__.py
{
    "name": "L9 Match Regression Detector",
    "version": "1.0.0",
    "depends": ["plasticos_intake"],
    "data": [
        "data/regression_cron.xml"
    ],
    "installable": True,
}
File: Plasticos/l9_regression/__init__.py
from . import models
File: Plasticos/l9_regression/models/__init__.py
from . import regression_detector
File: Plasticos/l9_regression/models/regression_detector.py
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
File: Plasticos/l9_regression/data/regression_cron.xml
<odoo>
    <record id="cron_l9_regression_detector" model="ir.cron">
        <field name="name">L9 Match Regression Detector</field>
        <field name="model_id" ref="model_l9_regression_detector"/>
        <field name="state">code</field>
        <field name="code">model.run_regression_check()</field>
        <field name="interval_number">30</field>
        <field name="interval_type">minutes</field>
    </record>
</odoo>