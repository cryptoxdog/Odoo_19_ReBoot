

1️⃣ Hard Idempotency (No Duplicate Emissions)
Goal:

Same intake + same packet_version
→ can never emit twice unless forced.



Logistics:

🚦 Definitive Linda Flow
1️⃣ Sales Order Button Pressed
→ Create linda.load
→ state = awaiting_ready_confirmation

2️⃣ READY Confirmed
Store:

confirmed_by

confirmed_at

→ state = ready_confirmed

3️⃣ Carrier Rate Confirmed
Store:

carrier_id

rate_amount

rate_confirmed_at

→ state = carrier_rate_confirmed

4️⃣ Appointment Scheduling
If required:

pickup_scheduled

delivery_scheduled

→ state = scheduled

5️⃣ Dispatch
Allowed only if:

ready_confirmed

carrier_rate_confirmed

scheduling satisfied

→ state = dispatched

6️⃣ Pickup → Transit → Delivery
State transitions traced.

7️⃣ Close
Allowed only if:

pickup BOL attached

delivery BOL attached

→ state = closed

🧱 What We Build Next
Now that logistics files are complete and friction removed:

Next output will be:

Full production-grade linda_logistics module rebuild

Clean state machine

SO button hook

Appointment engine

Rate confirmation workflow

BOL gating

Mail template hooks

Trace integration

Cron follow-ups


======


🧱 Proper Separation of Domains
We now have 4 distinct modules:

plasticos_transaction   ← lifecycle + accounting spine
plasticos_commission    ← commission logic only
plasticos_documents     ← compliance + document tracking
linda_logistics         ← execution
Each one owns its domain.

No cross-pollution.

📦 What Goes Where (Authoritative)
1️⃣ plasticos_documents
Owns:

document model

tag model

document rules

required-doc logic

missing-doc cron

compliance status

verification status

override tracking

Does NOT contain:

margin

commission

invoice logic

2️⃣ plasticos_commission
Owns:

commission rules

commission calculation

override logic

commission freeze at close

Does NOT contain:

documents

compliance

accounting posting logic

3️⃣ plasticos_transaction
Owns:

SO / PO linkage

Accounting linkage

Linda linkage

State lifecycle

Margin computation

Delegates:

commission to commission module

compliance to documents module

Transaction asks:

documents.is_compliant(transaction_id)
commission.calculate(transaction_id)
It does not implement either internally.

4️⃣ linda_logistics
Owns:

rate

carrier

scheduling

state transitions

execution artifacts

It may attach documents, but does not evaluate compliance.

==========================================
==========================================

🔥 Correct Governance Model
Documents module exposes:

get_compliance_status(res_model, res_id)
get_missing_documents(res_model, res_id)
can_post_invoice(res_model, res_id)
can_close_transaction(res_model, res_id)
Transaction simply checks these.

That’s clean architecture.

==========================================
==========================================


4️⃣ Commission Calculation Rules
Step 1 — Revenue
revenue_total = customer_invoice.amount_total
Step 2 — Cost
cost_total =
    sum(vendor_bill.amount_total)
  + sum(freight_bill.amount_total)
Step 3 — Gross Margin
gross_margin = revenue_total - cost_total
Step 4 — Commission
If commission_override_flat exists:

commission_amount = commission_override_flat
Else:

commission_amount = gross_margin * commission_rule.percentage
Step 5 — Net Margin
net_margin = gross_margin - commission_amount
5️⃣ Commission Rule Model
plasticos.commission.rule


==========================================
==========================================




==========================================
==========================================





==========================================
==========================================





==========================================
==========================================




==========================================
==========================================