from osv import fields, osv


class account_account(osv.osv):
    _inherit = 'account.account'

    _columns = {
        'ledger_types': fields.many2many('alternate_ledger.ledger_type',
                                         string='Ledger Types')
    }
