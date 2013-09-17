from openerp.osv import fields, osv
from openerp.tools.translate import _

_enum_ledger_type = [
    ('ledger_a', _('Ledger A')),
    ('ledger_b', _('Ledger B')),
    ('ledger_c', _('Ledger C')),
    ('ledger_d', _('Ledger D')),
    ('ledger_e', _('Ledger E')),
]

class ledger_type(osv.Model):
    _name = 'alternate_ledger.ledger_type'
    
    _columns = {
        'name': fields.char(
            _('Name'), size=256, required=True),
        'type': fields.selection(
            _enum_ledger_type, _('Ledger Type'), required=True),
    }

    _sql_constraint = [
        ('name', "UNIQUE('name')", 'Name has to be unique !'),
    ]
