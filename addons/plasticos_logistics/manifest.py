{
    "name": "Plasticos Logistics Engine",
    "version": "1.0.0",
    "depends": ["sale_management", "stock", "mail", "l9_trace"],
    "data": [
        "security/ir.model.access.csv",
        "views/load_views.xml",
        "views/sale_order_button.xml",
        "data/cron.xml",
    ],
    "installable": True,
    "application": False,
}
