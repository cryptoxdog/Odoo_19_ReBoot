from odoo.tests.common import TransactionCase


class TestMigrationSafety(TransactionCase):

    def test_no_duplicate_invoice_links(self):
        duplicates = self.env.cr.execute("""
            SELECT customer_invoice_id
            FROM plasticos_transaction
            WHERE customer_invoice_id IS NOT NULL
            GROUP BY customer_invoice_id
            HAVING COUNT(*) > 1;
        """)
        self.assertIsNone(duplicates)
