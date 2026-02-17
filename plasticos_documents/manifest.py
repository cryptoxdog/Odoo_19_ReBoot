{
    "name": "Plasticos Documents Engine",
    "version": "1.0.0",
    "depends": ["base", "mail"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/document_tag_views.xml",
        "views/document_rule_views.xml",
        "views/document_views.xml",
        "data/cron.xml"
    ],
    "installable": True,
    "application": False,
}
