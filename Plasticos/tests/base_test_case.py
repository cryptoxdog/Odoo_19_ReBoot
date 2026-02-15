from odoo.tests.common import TransactionCase


class PlasticosBaseTest(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.Partner = cls.env["res.partner"]
        cls.Intake = cls.env["plasticos.intake"]
        cls.MaterialProfile = cls.env["plasticos.material.profile"]
        cls.TraceRun = cls.env["l9.trace.run"]

    def create_partner(self, name="Test Supplier"):
        return self.Partner.create({"name": name})

    def create_intake(self, partner, payload):
        payload.update({"partner_id": partner.id})
        return self.Intake.create(payload)

    def assert_trace_created(self):
        count = self.TraceRun.search_count([])
        self.assertGreater(count, 0, "Trace run not created")


