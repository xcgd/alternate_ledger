# -*- coding: utf-8 -*-
{
    "name": "Alternate Ledger",
    "version": "1.2.3",
    "author": "XCG Consulting",
    "category": 'Accounting',
    "description": '''Allow the creation of new accounting ledgers that store
        separate transactions.''',
    'website': 'http://www.openerp-experts.com',
    'init_xml': [],
    "depends": [
        'base',
        'account_streamline',
        'analytic_structure',
    ],
    "data": [
        'security/ir.model.access.csv',
        'views/account_view.xml',
        'views/ledger_type.xml',
        'views/menu.xml',
        'views/account_journal.xml',
        
    ],
    'js': [
        'static/src/js/account_move_line_alternate_quickadd.js',
    ],
    'qweb': [
        'static/src/xml/account_move_line_alternate_quickadd.xml',
    ],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
