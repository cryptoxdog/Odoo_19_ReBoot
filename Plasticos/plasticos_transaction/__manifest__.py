{
    "name": "Plasticos Transaction Engine",
    "version": "1.0.0",
    "depends": [
        "base",
        "mail",
        "account",
        "sale_management",
        "purchase",
        "linda_logistics"
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/commission_rule_views.xml",
        "views/transaction_views.xml"
    ],
    "installable": True,
    "application": False,
}
