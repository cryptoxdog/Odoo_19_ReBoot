from odoo import models, fields
from odoo.addons.l9_trace.services.trace_kernel import TraceKernel
from odoo.addons.l9_trace.services.correlation import new_correlation_id


class LindaDispatch(models.Model):
    _name = "linda.dispatch"
    _description = "Linda Dispatch"

    name = fields.Char(required=True)
    state = fields.Selection([
        ("quoted", "Quoted"),
        ("dispatched", "Dispatched"),
        ("picked_up", "Picked Up"),
        ("delivered", "Delivered"),
        ("closed", "Closed"),
    ], default="quoted")

    def action_transition(self, new_state):
        for rec in self:
            correlation_id = new_correlation_id()
            trace = TraceKernel(self.env, service_name="linda_dispatch", correlation_id=correlation_id)
            span = trace.start_span("state_transition", "system")
            rec.state = new_state
            trace.event(span, "dispatch_state_changed", {
                "dispatch_id": rec.id,
                "new_state": new_state
            })
