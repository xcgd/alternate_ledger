from openerp.osv import fields, osv
from openerp.tools.translate import _

class account_balance_ledger_report(osv.TransientModel):
    _inherit = 'account.balance.report'
    _name = 'account.balance.report'

    _columns = {
        'ledger_id': fields.many2one(
            'alternate_ledger.ledger_type',
            _('Ledger Type'),
            required=True,
        ),
        'no_opening': fields.boolean('No Opening'),
    }

    def _get_ledger_a(self, cr, uid, context=None):
        ledger_osv = self.pool.get('alternate_ledger.ledger_type')
        ids = ledger_osv.search(
            cr, uid, [], context=context)
        if ids:
            return ids[0]
        return None

    _defaults = {
        'ledger_id': _get_ledger_a,
    }
