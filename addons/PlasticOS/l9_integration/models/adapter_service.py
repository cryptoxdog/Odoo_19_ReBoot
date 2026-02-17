from odoo import models, fields
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

    EXPECTED_MATCH_BEHAVIOR = {
        "pp_regrind_medical": {"min_score": 0.8},
        "hdpe_drum_grind": {"min_score": 0.5},
    }

    def _get_param(self, key, default=None):
        return self.env["ir.config_parameter"].sudo().get_param(key, default)

    def run_buyer_match(self, intake):
        if not intake:
            raise UserError("Missing intake record.")

        if (
            getattr(intake, "last_packet_version", None) == self.PACKET_VERSION
            and getattr(intake, "last_packet_id", None)
        ):
            raise UserError(
                f"Packet already emitted for version {self.PACKET_VERSION}"
            )

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

            intake.write({
                "last_packet_id": packet_id,
                "last_packet_version": self.PACKET_VERSION,
                "last_packet_payload": packet,
                "last_packet_ts": fields.Datetime.now(),
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
            if "ranked_buyers" not in resp:
                raise UserError("Invalid L9 response: missing ranked_buyers")
            if not isinstance(resp["ranked_buyers"], list):
                raise UserError("ranked_buyers must be list")

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
            intake.write({
                "match_status": "error",
                "match_response": {"error": str(e)},
            })
            raise
        finally:
            trace.finalize(outcome=outcome)

    def emit_raw_packet(self, packet):
        endpoint = self._get_param("l9.endpoint_url")
        api_key = self._get_param("l9.api_key")
        timeout = float(self._get_param("l9.timeout_sec", "30"))
        correlation_id = new_correlation_id()
        trace = TraceKernel(self.env, service_name="odoo_plasticos", correlation_id=correlation_id)
        span_emit = trace.start_span("http_emit_raw", "tool")
        resp = post_json(
            url=endpoint,
            payload=packet,
            api_key=api_key,
            timeout_sec=timeout,
            trace=trace,
            span_id=span_emit,
        )
        trace.finalize(outcome="ok")
        return resp
