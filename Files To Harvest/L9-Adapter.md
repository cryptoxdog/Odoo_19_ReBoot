Plasticos/
└── l9_adapter/
    ├── __manifest__.py
    ├── __init__.py
    ├── models/
    │   ├── __init__.py
    │   └── adapter_service.py
    ├── services/
    │   ├── __init__.py
    │   ├── packet_builder.py
    │   ├── http_client.py
    │   └── idempotency.py
    ├── security/
    │   └── ir.model.access.csv
FILE: Plasticos/l9_adapter/__manifest__.py
{
    "name": "L9 Adapter",
    "version": "1.0.0",
    "summary": "Packet boundary from Odoo to L9",
    "author": "PlasticOS",
    "depends": [
        "base",
        "l9_trace",
        "plasticos_intake",
        "plasticos_material",
        "plasticos_processing"
    ],
    "data": [
        "security/ir.model.access.csv"
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3"
}
FILE: Plasticos/l9_adapter/__init__.py
from . import models
from . import services
FILE: Plasticos/l9_adapter/models/__init__.py
from . import adapter_service
FILE: Plasticos/l9_adapter/models/adapter_service.py
from odoo import models
from odoo.exceptions import UserError

from ..services.packet_builder import build_intake_packet
from ..services.http_client import post_json
from ..services.idempotency import make_packet_id

from odoo.addons.l9_trace.services.trace_kernel import TraceKernel
from odoo.addons.l9_trace.services.correlation import new_correlation_id


class L9AdapterService(models.AbstractModel):
    _name = "l9.adapter.service"
    _description = "L9 Adapter Service"

    PACKET_VERSION = "1.0"
    EVENT_TYPE = "BUYER_MATCH_REQUEST"

    def _get_param(self, key, default=None):
        return self.env["ir.config_parameter"].sudo().get_param(key, default)

    def run_buyer_match(self, intake):
        if not intake:
            raise UserError("Missing intake record.")

        endpoint = self._get_param("l9.endpoint_url")
        api_key = self._get_param("l9.api_key")
        timeout = float(self._get_param("l9.timeout_sec", "30"))

        if not endpoint:
            raise UserError("Missing system parameter: l9.endpoint_url")

        correlation_id = new_correlation_id()
        trace = TraceKernel(self.env, service_name="odoo_plasticos", correlation_id=correlation_id)

        outcome = "ok"
        try:
            span_build = trace.start_span("packet_build", "system")
            packet_id = make_packet_id(intake.id, self.PACKET_VERSION)
            packet = build_intake_packet(
                intake=intake,
                packet_id=packet_id,
                packet_version=self.PACKET_VERSION,
                event_type=self.EVENT_TYPE,
                correlation_id=correlation_id,
                run_id=trace.run_id,
            )
            trace.event(span_build, "packet_built", {
                "packet_id": packet_id,
                "packet_version": self.PACKET_VERSION,
                "event_type": self.EVENT_TYPE,
            })

            span_emit = trace.start_span("http_emit", "tool", parent_span_id=span_build)
            resp = post_json(
                url=endpoint,
                payload=packet,
                api_key=api_key,
                timeout_sec=timeout,
                trace=trace,
                span_id=span_emit,
            )

            span_parse = trace.start_span("response_parse", "system", parent_span_id=span_emit)
            if not isinstance(resp, dict):
                raise UserError("Invalid L9 response: expected JSON object.")

            # Strict writeback: only match fields
            span_write = trace.start_span("writeback", "system", parent_span_id=span_parse)
            intake.write({
                "match_status": "matched" if resp.get("ranked_buyers") else "rejected",
                "match_response": resp,
            })
            trace.event(span_write, "writeback_ok", {
                "match_status": intake.match_status,
                "ranked_buyers_count": len(resp.get("ranked_buyers", [])) if isinstance(resp.get("ranked_buyers", []), list) else None
            })

            return resp

        except Exception as e:
            outcome = "error"
            # Do not mutate intake fields other than status/response on failure
            intake.write({
                "match_status": "error",
                "match_response": {"error": str(e)},
            })
            raise
        finally:
            trace.finalize(outcome=outcome)
FILE: Plasticos/l9_adapter/services/__init__.py
from . import packet_builder
from . import http_client
from . import idempotency
FILE: Plasticos/l9_adapter/services/idempotency.py
import hashlib

def make_packet_id(intake_id: int, packet_version: str) -> str:
    raw = f"intake:{intake_id}:v:{packet_version}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]
FILE: Plasticos/l9_adapter/services/packet_builder.py
def build_intake_packet(
    intake,
    packet_id: str,
    packet_version: str,
    event_type: str,
    correlation_id: str,
    run_id: str,
):
    # deterministic, explicit mapping only
    return {
        "packet_id": packet_id,
        "packet_version": packet_version,
        "event_type": event_type,
        "correlation_id": correlation_id,
        "trace_run_id": run_id,
        "payload": {
            "intake": {
                "id": intake.id,
                "name": intake.name,
                "partner_id": intake.partner_id.id if intake.partner_id else None,
                "facility_id": intake.facility_id.id if hasattr(intake, "facility_id") and intake.facility_id else None,
                "processing_profile_id": intake.processing_profile_id.id if hasattr(intake, "processing_profile_id") and intake.processing_profile_id else None,
            },
            "material_snapshot": {
                "polymer": intake.polymer,
                "form": intake.form,
                "color": intake.color,
                "source_type": intake.source_type,
                "grade_hint": intake.grade_hint,
            },
            "observed_quality": {
                "mfi_value": intake.mfi_value,
                "density_value": intake.density_value,
                "moisture_ppm": intake.moisture_ppm,
                "contamination_total_pct": intake.contamination_total_pct,
                "has_metal": intake.has_metal,
                "has_fr": intake.has_fr,
                "has_residue": intake.has_residue,
                "filler_type": intake.filler_type,
                "filler_pct": intake.filler_pct,
                "contamination_notes": intake.contamination_notes,
            },
            "origin": {
                "origin_application": intake.origin_application,
                "origin_sector": intake.origin_sector,
                "origin_process_type": intake.origin_process_type,
            },
            "commercial": {
                "quantity_per_load_lbs": intake.quantity_per_load_lbs,
                "loads_per_month": intake.loads_per_month,
                "deal_type": intake.deal_type,
                "contract_duration_months": intake.contract_duration_months,
            },
            "freeform": {
                "material_hint_text": intake.material_hint_text,
            },
        },
    }
FILE: Plasticos/l9_adapter/services/http_client.py
import json
import time
import urllib.request
from urllib.error import URLError, HTTPError

def post_json(url, payload, api_key=None, timeout_sec=30, trace=None, span_id=None):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")

    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8")
            latency = time.time() - start
            if trace and span_id:
                trace.event(span_id, "http_ok", {
                    "latency_sec": latency,
                    "status": getattr(resp, "status", None),
                    "request_bytes": len(body),
                    "response_bytes": len(raw),
                })
            return json.loads(raw) if raw else {}
    except HTTPError as e:
        latency = time.time() - start
        if trace and span_id:
            trace.event(span_id, "http_error", {
                "latency_sec": latency,
                "status": getattr(e, "code", None),
                "error": str(e),
            })
        raise
    except URLError as e:
        latency = time.time() - start
        if trace and span_id:
            trace.event(span_id, "http_error", {
                "latency_sec": latency,
                "status": None,
                "error": str(e),
            })
        raise

FILE: Plasticos/l9_adapter/security/ir.model.access.csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_l9_adapter_service,l9.adapter.service,model_l9_adapter_service,base.group_system,1,1,1,1
