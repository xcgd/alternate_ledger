# -*- coding: utf-8 -*-
{
    "name": "Alternate Ledger",
    "version": "0.1",
    "author": "XCG Consulting",
    "category": 'Accounting',
    "description": """Enhancements to the account module to allow user to
                   exclude openning journal when generating trial balance.""",
    'website': 'http://www.openerp-experts.com',
    'init_xml': [],
    "depends": [
        'base',
        'account_accountant',
    ],
    "data": [
        'wizard/account_report_alternate_account_balance_view.xml',
        'views/account_view.xml',
        'views/ledger_type.xml',
        'security/ir.model.access.csv',
        'views/menu.xml',
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
