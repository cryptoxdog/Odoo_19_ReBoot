from odoo.tests.common import TransactionCase
from odoo import api
from psycopg2 import OperationalError


class TestConcurrency(TransactionCase):

    def test_duplicate_vendor_bill_link_race(self):
        tx1 = self.env["plasticos.transaction"].create({})
        tx2 = self.env["plasticos.transaction"].create({})

        bill = self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": self.env.ref("base.res_partner_1").id,
        })

        tx1.vendor_bill_ids = [(4, bill.id)]

        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                tx2.vendor_bill_ids = [(4, bill.id)]
                self.env.cr.flush()
