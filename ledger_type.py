from openerp.osv import fields, osv
from openerp.tools.translate import _


class ledger_type(osv.Model):
    _name = 'alternate_ledger.ledger_type'

    _columns = {
        'name': fields.char(
            _('Name'), size=256, required=True),
    }

    _order = 'name'

    _sql_constraint = [
        ('name', "UNIQUE('name')", 'Name has to be unique !'),
    ]
