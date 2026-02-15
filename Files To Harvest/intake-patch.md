

Step 1: Enforce Packet Uniqueness at Model Level
PATCH: plasticos_intake/models/intake.py
Add SQL constraint:

@@
     last_packet_id = fields.Char(index=True)
     last_packet_version = fields.Char()
@@
+    _sql_constraints = [
+        (
+            "unique_packet_per_version",
+            "unique(last_packet_id, last_packet_version)",
+            "Duplicate packet emission detected."
+        )
+    ]
This prevents DB-level duplication.

Step 2: Adapter Refuses Duplicate
PATCH: l9_adapter/models/adapter_service.py
Modify run_buyer_match:

@@
     def run_buyer_match(self, intake):
@@
+        # Hard idempotency check
+        if (
+            intake.last_packet_version == self.PACKET_VERSION
+            and intake.last_packet_id
+        ):
+            raise UserError(
+                f"Packet already emitted for version {self.PACKET_VERSION}"
+            )
Step 3: Persist Packet After Build
Inside run_buyer_match, after packet built:

@@
 packet = build_intake_packet(...)
 
+ intake.write({
+     "last_packet_id": packet_id,
+     "last_packet_version": self.PACKET_VERSION,
+     "last_packet_payload": packet,
+     "last_packet_ts": fields.Datetime.now(),
+ })
Now duplicate emission is impossible without explicit override.

Machine-grade.

2️⃣ Five Additional Hardening Layers
🔥 1. Transaction Boundary Lock (Row-Level Safety)
Prevent race condition where two workers emit same intake.

Add record lock before emission:

self.env.cr.execute(
    "SELECT id FROM plasticos_intake WHERE id = %s FOR UPDATE",
    (intake.id,)
)
Place this at top of run_buyer_match.

Guarantees:

No concurrent duplicate emissions

No double writeback

🔥 2. Response Schema Validation
Before writeback:

if "ranked_buyers" not in resp:
    raise UserError("Invalid L9 response: missing ranked_buyers")
And enforce structure:

if not isinstance(resp["ranked_buyers"], list):
    raise UserError("ranked_buyers must be list")
Never trust upstream blindly.

🔥 3. Strict Writeback Whitelist
Instead of:

intake.write(resp)
Only allow:

intake.write({
    "match_status": status,
    "match_response": resp,
})
Never allow L9 to mutate:

polymer

form

quantity

etc.

Boundary must remain sacred.

🔥 4. Timeout + Circuit Breaker
Add failure counter in adapter:

Add fields to intake:

l9_failure_count = fields.Integer(default=0)
l9_disabled = fields.Boolean(default=False)
In adapter:

except Exception:
    intake.l9_failure_count += 1
    if intake.l9_failure_count >= 3:
        intake.l9_disabled = True
Now unstable intakes auto-disable.

Prevents infinite retry storms.

🔥 5. Drift Snapshot Hash
Before emit:

import hashlib
import json

snapshot = json.dumps(packet["payload"], sort_keys=True).encode()
hashval = hashlib.sha256(snapshot).hexdigest()
Store:

intake.last_payload_hash = hashval
On replay:

Recalculate and compare.

If changed → data drift occurred.

You now detect silent schema mutation.

3️⃣ Optional Ultra-Enterprise Additions
If you want true operating-system-grade behavior:

A) Environment Tagging
Add to packet:

"environment": self._get_param("l9.environment", "dev")
Prevents cross-environment contamination.

B) Deterministic Ordering
When building packet:

Sort keys.
Sort arrays.

Prevents hash drift due to ordering.

C) Trace Span Failure Classification
Add categories:

network_error

schema_error

writeback_error

upstream_error

Improves monitoring instantly.

D) Auto Health Metric
Add computed field:

l9_health_score = 1 - (l9_failure_count / 5)
Now you can dashboard L9 reliability inside Odoo.

E) Hard Freeze Packet Schema
Add test:

EXPECTED_PACKET_KEYS = {...}
assert set(packet.keys()) == EXPECTED_PACKET_KEYS
Prevents silent payload mutation by future dev.