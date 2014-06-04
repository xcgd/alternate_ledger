from openerp.osv import (
    osv,
    fields
)


class account_journal(osv.Model):
    _inherit = 'account.journal'

    _columns = {
        'version_number': fields.char(u"Version", size=8),
        'is_active': fields.boolean(u"Is Active"),
    }
