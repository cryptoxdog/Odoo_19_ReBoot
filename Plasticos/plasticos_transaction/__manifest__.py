{
    "name": "Plasticos Transaction Spine",
    "version": "1.0.0",
    "depends": [
        "base",
        "mail",
        "account",
        "sale_management",
        "purchase",
        "logistics",
        "plasticos_documents",
        "plasticos_commission"
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/security_hardening.xml",
        "security/commission_acl.xml",
        "data/sequence.xml",
        "data/audit_cron.xml",
        "views/transaction_views.xml"
    ],
    "installable": True,
    "application": False,
}
