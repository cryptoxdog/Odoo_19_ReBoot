🔥 TECHNICAL DEBT KILL LIST
Priority ordered. Brutal. Surgical.

1️⃣ Transaction Sequence Generator
Risk: Medium
Impact: Audit integrity + human sanity

Problem:
name = "New" placeholder logic.

Fix:

Add ir.sequence

Enforce unique constraint

Remove manual naming

Why:
You don’t want TX-duplicates when under load.

2️⃣ Idempotent Linking (Critical)
Risk: High
Impact: Silent duplication bugs

Current risk:
Multiple action_post() calls could:

Re-append vendor bills

Re-append freight bills

Re-append POs

Fix:
Before linking, check existence:

if rec.id not in tx.vendor_bill_ids.ids:
Why:
Odoo allows re-trigger.
You must guard.

3️⃣ Commission Freeze Integrity
Risk: High
Impact: Retroactive payout mutation

Problem:
If gross margin changes after close, commission could drift.

Fix:

Once commission_locked=True, prevent recompute.

Override write() to block financial changes when closed.

Add guard:

if rec.state == "closed" and any(financial_fields in vals):
    raise UserError(...)
4️⃣ Document Rule Resolution Logic
Risk: Medium

You said:
Per-client optional.

Right now:
Rules ignore client dimension.

Fix:
Rule resolution order:

Client-specific rule

Global rule

Most restrictive wins

Otherwise compliance will behave unpredictably.

5️⃣ Cron Stub Is Fake
Risk: Medium

Current cron does nothing meaningful.

Fix:
Cron should:

Scan active transactions

Compute missing docs

Post chatter message if missing

Optionally create activity

Otherwise compliance drift happens silently.

6️⃣ Financial Field Store Dependencies
Risk: Medium

Your compute methods depend on:

customer_invoice_id.amount_total
vendor_bill_ids.amount_total
But not on bill state.

If bill updated after posting:
Margins may not recompute.

Fix:
Include .state dependency or enforce immutability after posting.

7️⃣ Refund / Credit Note Blind Spot
Risk: High

You currently ignore:

Credit notes

Reversals

Adjustments

That will break margin reality.

Fix:
Include move_type in:

out_refund
in_refund
Adjust totals accordingly.

8️⃣ Payment State Awareness Missing
Risk: Medium

Posting ≠ paid.

If you pay commission before collecting money,
cash flow risk.

Fix (optional but recommended):

Add:

is_fully_paid = all(invoices.payment_state == "paid")
Gate commission release if needed.

9️⃣ Missing Indexes
Risk: Low now / High later

Add index=True on:

sale_order_id

linda_load_id

customer_invoice_id

state

compliance_status

Database will thank you at 10k+ deals.

🔟 No Write Guards on Closed Transaction
Risk: High

Currently:
You can modify linked bills after close.

Fix:

Override write():

Block modification of:

invoice fields

bill fields

commission_rule_id

financial fields

Unless admin override.

1️⃣1️⃣ Multi-Load Blind Spot
Future risk:
1 SO → multiple Linda loads.

Right now:
Single linda_load_id.

Fix later:
Make it Many2many or One2many.

Not urgent for MVP.

1️⃣2️⃣ Lane Reuse Rule Not Persisted
You described 30-day rate reuse.

It is not implemented as:

Lane model

Rate history model

Right now it’s conceptual.

This will cause friction later.

1️⃣3️⃣ Commission Override Field Missing
Flat override per load not yet implemented cleanly.

You need:

commission_override_flat
Priority: Medium.

1️⃣4️⃣ Missing Override Audit Log
Documents override exists.
Transaction override does not.

Add:

override_user_id

override_reason

override_timestamp

For closing override scenarios.

1️⃣5️⃣ No KPI Layer
You have no:

cycle time metric

margin per rep report

compliance rate

stuck-in-state detection

Not critical now.
Critical at scale.

🧠 Root Technical Risks Summary
Most dangerous current weaknesses:

Idempotency gaps

Commission mutation risk

Credit note blind spot

Write-guard absence

Cron being decorative

Everything else is maturity polish.

🎯 Immediate Kill Order (Do These First)
Add write guards to transaction

Add idempotent linking

Lock commission after close

Handle refunds in margin

Replace cron stub with real compliance scan

Add transaction sequence

Do these and your spine becomes resilient.

🚨 Brutal Truth
Architecture: clean.
Logic: correct.
Resilience: not yet hardened.