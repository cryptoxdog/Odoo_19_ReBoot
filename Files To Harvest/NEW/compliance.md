Good. We formalize the compliance API properly.

No ambiguity. No hidden logic. Deterministic behavior.

This lives in:

```
Plasticos/plasticos_documents/models/compliance_service.py
```

Full production-ready service below.

---

## 📁 Plasticos/plasticos_documents/models/compliance_service.py

```python
from odoo import models


class PlasticosComplianceService(models.AbstractModel):
    _name = "plasticos.compliance.service"
    _description = "Plasticos Compliance Service"


    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    def get_missing_documents(self, res_model, res_id):
        rules = self._get_applicable_rules(res_model, res_id)

        missing = []

        for rule in rules:
            if not self._is_rule_satisfied(rule, res_model, res_id):
                missing.append(rule.tag_id.code)

        return missing


    def get_compliance_status(self, res_model, res_id):
        missing = self.get_missing_documents(res_model, res_id)

        if missing:
            return {
                "status": "missing",
                "missing_tags": missing,
            }

        return {
            "status": "compliant",
            "missing_tags": [],
        }


    def can_post_invoice(self, res_model, res_id):
        rules = self._get_applicable_rules(res_model, res_id)

        for rule in rules.filtered(lambda r: r.required_for_invoice):
            if not self._is_rule_satisfied(rule, res_model, res_id):
                return False

        return True


    def can_close_transaction(self, res_model, res_id):
        rules = self._get_applicable_rules(res_model, res_id)

        for rule in rules.filtered(lambda r: r.required_for_close):
            if not self._is_rule_satisfied(rule, res_model, res_id):
                return False

        return True


    # ---------------------------------------------------------
    # Internal Resolution Logic
    # ---------------------------------------------------------

    def _get_applicable_rules(self, res_model, res_id):
        record = self.env[res_model].browse(res_id)

        client = getattr(record, "partner_id", False)

        domain = [
            ("res_model", "=", res_model),
            ("active", "=", True),
        ]

        rules = self.env["plasticos.document.rule"].search(domain)

        # Client-specific override rules
        if client:
            client_rules = rules.filtered(
                lambda r: r.client_id and r.client_id.id == client.id
            )

            if client_rules:
                return client_rules

        # Fallback to global rules
        return rules.filtered(lambda r: not r.client_id)


    def _is_rule_satisfied(self, rule, res_model, res_id):
        docs = self.env["plasticos.document"].search([
            ("res_model", "=", res_model),
            ("res_id", "=", res_id),
            ("tag_id", "=", rule.tag_id.id),
            "|",
            ("verified", "=", True),
            ("override", "=", True),
        ])

        return bool(docs)
```

---

# What This Now Guarantees

✔ Deterministic rule resolution
✔ Client override support
✔ Invoice gating separate from close gating
✔ Clear API boundary
✔ No logic leakage into transaction
✔ No circular dependencies

---

# Correct Usage in Transaction

Replace previous calls with:

```python
service = self.env["plasticos.compliance.service"]

if not service.can_post_invoice("plasticos.transaction", tx.id):
    raise UserError("Missing required documents for invoice.")

if not service.can_close_transaction("plasticos.transaction", tx.id):
    raise UserError("Missing required documents for close.")
```

---

# Why This Is Clean

* Compliance rules live in documents module
* Transaction only queries the service
* Commission untouched
* Logistics untouched
* Accounting untouched

You now have a proper domain boundary.

---

If you want next, I recommend:

Add compliance caching on transaction (stored field updated via cron + document create/write).

It removes recomputation overhead and improves scalability.

Say:
“Add compliance cache layer.”
