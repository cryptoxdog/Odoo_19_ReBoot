from odoo.tests.common import TransactionCase
import hashlib


class TestDeterministicReplay(TransactionCase):

    def _snapshot_hash(self, tx):
        payload = (
            tx.revenue_total,
            tx.cost_total,
            tx.gross_margin,
            tx.commission_amount,
            tx.net_margin,
            tx.commission_locked,
        )
        return hashlib.sha256(str(payload).encode()).hexdigest()

    def _build_transaction(self):
        so = self.env["sale.order"].create({
            "partner_id": self.env.ref("base.res_partner_1").id,
        })

        tx = self.env["plasticos.transaction"].create({
            "sale_order_id": so.id,
        })

        invoice = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": so.partner_id.id,
            "invoice_line_ids": [(0, 0, {
                "name": "Revenue",
                "quantity": 1,
                "price_unit": 1000,
            })],
        })
        invoice.action_post()
        tx.customer_invoice_id = invoice.id

        bill = self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": so.partner_id.id,
            "invoice_line_ids": [(0, 0, {
                "name": "Cost",
                "quantity": 1,
                "price_unit": 600,
            })],
        })
        bill.action_post()
        tx.vendor_bill_ids = [(4, bill.id)]

        tx.action_activate()
        tx.action_close()

        return tx

    def test_replay_is_deterministic(self):
        tx1 = self._build_transaction()
        h1 = self._snapshot_hash(tx1)

        self.env.cr.rollback()

        tx2 = self._build_transaction()
        h2 = self._snapshot_hash(tx2)

        self.assertEqual(h1, h2)
