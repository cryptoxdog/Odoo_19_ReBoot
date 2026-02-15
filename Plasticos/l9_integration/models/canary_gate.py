from odoo import models, fields
import random


class L9CanaryConfig(models.Model):
    _name = "l9.canary.config"
    _description = "L9 Canary Configuration"

    enabled = fields.Boolean(default=False)
    canary_percentage = fields.Integer(default=10)
    canary_endpoint = fields.Char()


class L9CanaryGate(models.AbstractModel):
    _name = "l9.canary.gate"

    def should_use_canary(self):
        config = self.env["l9.canary.config"].search([], limit=1)
        if not config or not config.enabled:
            return False

        roll = random.randint(1, 100)
        return roll <= config.canary_percentage

    def resolve_endpoint(self, default_endpoint):
        config = self.env["l9.canary.config"].search([], limit=1)
        if self.should_use_canary() and config.canary_endpoint:
            return config.canary_endpoint
        return default_endpoint
