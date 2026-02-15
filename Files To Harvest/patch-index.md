
1️⃣ INDEX ADDITIONS
PATCH: Plasticos/l9_trace/models/trace_run.py
diff --git a/Plasticos/l9_trace/models/trace_run.py b/Plasticos/l9_trace/models/trace_run.py
index 1111111..2222222 100644
--- a/Plasticos/l9_trace/models/trace_run.py
+++ b/Plasticos/l9_trace/models/trace_run.py
@@ -8,8 +8,8 @@ class TraceRun(models.Model):
     _name = "l9.trace.run"
     _description = "L9 Trace Run"

-    run_id = fields.Char(required=True)
-    correlation_id = fields.Char()
+    run_id = fields.Char(required=True, index=True)
+    correlation_id = fields.Char(index=True)

     service_name = fields.Char(required=True)
     environment = fields.Char()
PATCH: Plasticos/plasticos_intake/models/intake.py
diff --git a/Plasticos/plasticos_intake/models/intake.py b/Plasticos/plasticos_intake/models/intake.py
index 3333333..4444444 100644
--- a/Plasticos/plasticos_intake/models/intake.py
+++ b/Plasticos/plasticos_intake/models/intake.py
@@ -15,7 +15,10 @@ class PlasticosIntake(models.Model):
     _name = "plasticos.intake"
     _description = "Plasticos Intake"

-    partner_id = fields.Many2one("res.partner", required=True)
+    partner_id = fields.Many2one(
+        "res.partner",
+        required=True,
+        index=True
+    )

     name = fields.Char(required=True)

@@ -25,8 +28,8 @@ class PlasticosIntake(models.Model):
-    polymer = fields.Char(required=True)
-    form = fields.Char(required=True)
+    polymer = fields.Char(required=True, index=True)
+    form = fields.Char(required=True, index=True)

     color = fields.Char()
2️⃣ PACKET PERSISTENCE + NORMALIZATION GATE
PATCH: Plasticos/plasticos_intake/models/intake.py
diff --git a/Plasticos/plasticos_intake/models/intake.py b/Plasticos/plasticos_intake/models/intake.py
index 4444444..5555555 100644
--- a/Plasticos/plasticos_intake/models/intake.py
+++ b/Plasticos/plasticos_intake/models/intake.py
@@ -120,6 +120,30 @@ class PlasticosIntake(models.Model):
     match_status = fields.Selection(
         [
             ("draft", "Draft"),
+            ("normalized", "Normalized"),
             ("matched", "Matched"),
             ("rejected", "Rejected"),
             ("error", "Error"),
         ],
         default="draft",
     )

     match_response = fields.Json()

+    # ---- L9 Packet Persistence ----
+
+    last_packet_id = fields.Char(index=True)
+    last_packet_version = fields.Char()
+    last_packet_payload = fields.Json()
+    last_packet_ts = fields.Datetime()
+
+    normalized = fields.Boolean(
+        default=False,
+        help="Must be True before adapter emits packet"
+    )
+
+    def action_mark_normalized(self):
+        for rec in self:
+            rec.write({
+                "normalized": True,
+                "match_status": "normalized"
+            })
3️⃣ ADD BUTTONS TO VIEW
PATCH: Plasticos/plasticos_intake/views/intake_views.xml
diff --git a/Plasticos/plasticos_intake/views/intake_views.xml b/Plasticos/plasticos_intake/views/intake_views.xml
index 6666666..7777777 100644
--- a/Plasticos/plasticos_intake/views/intake_views.xml
+++ b/Plasticos/plasticos_intake/views/intake_views.xml
@@ -20,6 +20,21 @@
                 <group>
                     <field name="match_status"/>
                 </group>
+
+                <group string="L9 Controls">
+                    <field name="normalized"/>
+                    <button
+                        name="action_mark_normalized"
+                        type="object"
+                        string="Mark Normalized"
+                        class="btn-primary"
+                    />
+                    <button
+                        name="action_run_buyer_match"
+                        type="object"
+                        string="Run Buyer Match"
+                        class="btn-success"
+                    />
+                </group>
             </sheet>
         </form>
     </record>

     
4️⃣ ADD RUN + REPLAY METHODS (Adapter Hook)
PATCH: Plasticos/plasticos_intake/models/intake.py
diff --git a/Plasticos/plasticos_intake/models/intake.py b/Plasticos/plasticos_intake/models/intake.py
index 5555555..8888888 100644
--- a/Plasticos/plasticos_intake/models/intake.py
+++ b/Plasticos/plasticos_intake/models/intake.py
@@ -160,6 +160,39 @@ class PlasticosIntake(models.Model):

     def action_mark_normalized(self):
         for rec in self:
             rec.write({
                 "normalized": True,
                 "match_status": "normalized"
             })

+    def action_run_buyer_match(self):
+        adapter = self.env["l9.adapter.service"]
+        for rec in self:
+            if not rec.normalized:
+                raise UserError("Intake must be normalized before match.")
+            adapter.run_buyer_match(rec)
+
+    def action_replay_last_packet(self):
+        adapter = self.env["l9.adapter.service"]
+        for rec in self:
+            if not rec.last_packet_payload:
+                raise UserError("No stored packet to replay.")
+            adapter.emit_raw_packet(rec.last_packet_payload)
(You will also add emit_raw_packet() in adapter next.)

5️⃣ STRICT SCORE ASSERTIONS
PATCH: Plasticos/tests/test_full_replay.py
diff --git a/Plasticos/tests/test_full_replay.py b/Plasticos/tests/test_full_replay.py
index 9999999..aaaaaaa 100644
--- a/Plasticos/tests/test_full_replay.py
+++ b/Plasticos/tests/test_full_replay.py
@@ -20,6 +20,22 @@ class TestFullReplay(PlasticosBaseTest):
         adapter.run_buyer_match(intake)
         intake.refresh()

+        self.assertIsInstance(intake.match_response, dict)
+
+        ranked = intake.match_response.get("ranked_buyers", [])
+        self.assertIsInstance(ranked, list)
+
+        for buyer in ranked:
+            score = buyer.get("score")
+            self.assertIsNotNone(score)
+            self.assertGreaterEqual(score, 0.0)
+            self.assertLessEqual(score, 1.0)
+
         self.assert_trace_created()
PATCH: Plasticos/tests/test_buyer_matching_matrix.py
diff --git a/Plasticos/tests/test_buyer_matching_matrix.py b/Plasticos/tests/test_buyer_matching_matrix.py
index bbbbbbb..ccccccc 100644
--- a/Plasticos/tests/test_buyer_matching_matrix.py
+++ b/Plasticos/tests/test_buyer_matching_matrix.py
@@ -18,6 +18,19 @@ class TestBuyerMatchingMatrix(PlasticosBaseTest):
             adapter.run_buyer_match(intake)
             intake.refresh()

+            ranked = intake.match_response.get("ranked_buyers", [])
+            self.assertIsInstance(ranked, list)
+
+            for buyer in ranked:
+                score = buyer.get("score")
+                self.assertIsNotNone(score)
+                self.assertGreaterEqual(score, 0.0)
+                self.assertLessEqual(score, 1.0)
+
         self.assert_trace_created()
6️⃣ Adapter: Add emit_raw_packet()
PATCH: Plasticos/l9_adapter/models/adapter_service.py
diff --git a/Plasticos/l9_adapter/models/adapter_service.py b/Plasticos/l9_adapter/models/adapter_service.py
index ddddddd..eeeeeee 100644
--- a/Plasticos/l9_adapter/models/adapter_service.py
+++ b/Plasticos/l9_adapter/models/adapter_service.py
@@ -95,3 +95,20 @@ class L9AdapterService(models.AbstractModel):
             trace.finalize(outcome=outcome)

+    def emit_raw_packet(self, packet):
+        endpoint = self._get_param("l9.endpoint_url")
+        api_key = self._get_param("l9.api_key")
+
+        correlation_id = new_correlation_id()
+        trace = TraceKernel(self.env, service_name="odoo_plasticos", correlation_id=correlation_id)
+
+        span_emit = trace.start_span("http_emit_raw", "tool")
+
+        resp = post_json(
+            url=endpoint,
+            payload=packet,
+            api_key=api_key,
+            timeout_sec=30,
+            trace=trace,
+            span_id=span_emit,
+        )
+
+        trace.finalize(outcome="ok")
+        return resp