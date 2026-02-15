
Plasticos/
└── plasticos_documents/
    ├── __manifest__.py
    ├── __init__.py
    ├── models/
    │   ├── __init__.py
    │   ├── document.py
    │   ├── document_tag.py
    │   ├── document_rule.py
    │   └── compliance_service.py
    ├── security/
    │   ├── security.xml
    │   └── ir.model.access.csv
    ├── views/
    │   ├── document_views.xml
    │   ├── document_tag_views.xml
    │   └── document_rule_views.xml
    └── data/
        └── cron.xml
Plasticos/plasticos_documents/manifest.py
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
Plasticos/plasticos_documents/init.py
from . import models
Plasticos/plasticos_documents/models/init.py
from . import document
from . import document_tag
from . import document_rule
from . import compliance_service
Plasticos/plasticos_documents/models/document_tag.py
from odoo import models, fields


class PlasticosDocumentTag(models.Model):
    _name = "plasticos.document.tag"
    _description = "Document Tag"

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)
Plasticos/plasticos_documents/models/document_rule.py
from odoo import models, fields


class PlasticosDocumentRule(models.Model):
    _name = "plasticos.document.rule"
    _description = "Document Compliance Rule"

    name = fields.Char(required=True)
    tag_id = fields.Many2one("plasticos.document.tag", required=True)
    res_model = fields.Char(required=True)
    client_id = fields.Many2one("res.partner")
    required_for_invoice = fields.Boolean(default=False)
    required_for_close = fields.Boolean(default=True)
    active = fields.Boolean(default=True)
Plasticos/plasticos_documents/models/document.py
from odoo import models, fields, api
from odoo.exceptions import UserError


class PlasticosDocument(models.Model):
    _name = "plasticos.document"
    _description = "Plasticos Document"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True)
    res_model = fields.Char(required=True, index=True)
    res_id = fields.Integer(required=True, index=True)

    attachment_id = fields.Many2one("ir.attachment", required=True)
    tag_id = fields.Many2one("plasticos.document.tag", required=True)

    verified = fields.Boolean(default=False)
    verified_by = fields.Many2one("res.users")
    verified_at = fields.Datetime()

    override = fields.Boolean(default=False)
    override_reason = fields.Text()

    active = fields.Boolean(default=True)

    @api.model
    def create(self, vals):
        record = super().create(vals)
        return record

    def action_verify(self):
        for rec in self:
            rec.verified = True
            rec.verified_by = self.env.user.id
            rec.verified_at = fields.Datetime.now()

    def action_override(self, reason):
        if not self.env.user.has_group("plasticos_documents.group_documents_manager"):
            raise UserError("Not authorized to override.")
        for rec in self:
            rec.override = True
            rec.override_reason = reason
Plasticos/plasticos_documents/models/compliance_service.py
from odoo import models


class PlasticosComplianceService(models.AbstractModel):
    _name = "plasticos.compliance.service"
    _description = "Compliance Service"

    def get_missing_documents(self, res_model, res_id):
        rules = self.env["plasticos.document.rule"].search([
            ("res_model", "=", res_model),
            ("active", "=", True)
        ])

        missing = []

        for rule in rules:
            docs = self.env["plasticos.document"].search([
                ("res_model", "=", res_model),
                ("res_id", "=", res_id),
                ("tag_id", "=", rule.tag_id.id),
                "|",
                ("verified", "=", True),
                ("override", "=", True)
            ])

            if not docs:
                missing.append(rule.tag_id.code)

        return missing

    def is_compliant(self, res_model, res_id):
        missing = self.get_missing_documents(res_model, res_id)
        return len(missing) == 0
Plasticos/plasticos_documents/security/security.xml
<odoo>
    <record id="group_documents_user" model="res.groups">
        <field name="name">Documents User</field>
    </record>

    <record id="group_documents_manager" model="res.groups">
        <field name="name">Documents Manager</field>
    </record>
</odoo>
Plasticos/plasticos_documents/security/ir.model.access.csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_document_user,document.user,model_plasticos_document,plasticos_documents.group_documents_user,1,1,1,0
access_document_manager,document.manager,model_plasticos_document,plasticos_documents.group_documents_manager,1,1,1,1
access_document_tag_admin,document.tag.admin,model_plasticos_document_tag,base.group_system,1,1,1,1
access_document_rule_admin,document.rule.admin,model_plasticos_document_rule,base.group_system,1,1,1,1
Plasticos/plasticos_documents/views/document_tag_views.xml
<odoo>
    <record id="view_document_tag_tree" model="ir.ui.view">
        <field name="name">plasticos.document.tag.tree</field>
        <field name="model">plasticos.document.tag</field>
        <field name="arch" type="xml">
            <tree>
                <field name="name"/>
                <field name="code"/>
                <field name="active"/>
            </tree>
        </field>
    </record>
</odoo>
Plasticos/plasticos_documents/views/document_rule_views.xml
<odoo>
    <record id="view_document_rule_tree" model="ir.ui.view">
        <field name="name">plasticos.document.rule.tree</field>
        <field name="model">plasticos.document.rule</field>
        <field name="arch" type="xml">
            <tree>
                <field name="name"/>
                <field name="tag_id"/>
                <field name="res_model"/>
                <field name="required_for_invoice"/>
                <field name="required_for_close"/>
                <field name="active"/>
            </tree>
        </field>
    </record>
</odoo>
Plasticos/plasticos_documents/views/document_views.xml
<odoo>
    <record id="view_document_tree" model="ir.ui.view">
        <field name="name">plasticos.document.tree</field>
        <field name="model">plasticos.document</field>
        <field name="arch" type="xml">
            <tree>
                <field name="name"/>
                <field name="res_model"/>
                <field name="res_id"/>
                <field name="tag_id"/>
                <field name="verified"/>
                <field name="override"/>
            </tree>
        </field>
    </record>
</odoo>
Plasticos/plasticos_documents/data/cron.xml
<odoo>
    <record id="cron_document_compliance_check" model="ir.cron">
        <field name="name">Document Compliance Audit</field>
        <field name="model_id" ref="model_plasticos_compliance_service"/>
        <field name="state">code</field>
        <field name="code">model.search([])</field>
        <field name="interval_number">6</field>
        <field name="interval_type">hours</field>
    </record>
</odoo>