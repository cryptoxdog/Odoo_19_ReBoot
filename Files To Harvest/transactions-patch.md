
🚛 LINDA LINKING
Plasticos/plasticos_transaction/models/linda_inherit.py
from odoo import models, fields


class LindaLoad(models.Model):
    _inherit = "linda.load"

    transaction_id = fields.Many2one("plasticos.transaction")


🔐 SECURITY
Plasticos/plasticos_transaction/security/ir.model.access.csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_transaction_user,transaction.user,model_plasticos_transaction,base.group_user,1,1,1,0


🖥 VIEW
Plasticos/plasticos_transaction/views/transaction_views.xml
<odoo>
    <record id="view_transaction_tree" model="ir.ui.view">
        <field name="name">plasticos.transaction.tree</field>
        <field name="model">plasticos.transaction</field>
        <field name="arch" type="xml">
            <tree>
                <field name="name"/>
                <field name="revenue_total"/>
                <field name="cost_total"/>
                <field name="gross_margin"/>
                <field name="compliance_status"/>
                <field name="state"/>
            </tree>
        </field>
    </record>
</odoo>



