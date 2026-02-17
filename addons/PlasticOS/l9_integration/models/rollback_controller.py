from odoo import models


class L9RollbackController(models.AbstractModel):
    _name = "l9.rollback.controller"

    def run_rollback_check(self):
        logs = self.env["l9.regression.log"].search([
            ("regression_detected", "=", True)
        ])

        if len(logs) > 5:
            config = self.env["l9.canary.config"].search([], limit=1)
            if config:
                config.enabled = False
