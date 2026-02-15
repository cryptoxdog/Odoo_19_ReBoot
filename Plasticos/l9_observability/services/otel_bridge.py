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
