# -*- coding: utf-8 -*-
##############################################################################
#
#    Alternate Ledger, for OpenERP
#    Copyright (C) 2013 XCG Consulting (http://odoo.consulting)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name": "Alternate Ledger",
    "version": "1.7",
    "author": "XCG Consulting",
    "category": 'Accounting',
    "description": '''Allow the creation of new accounting ledgers that store
        separate transactions.''',
    'website': 'http://odoo.consulting/',
    'init_xml': [],
    "depends": [
        'base',
        'account_streamline',
    ],
    "data": [
        'security/ir.model.access.csv',
        'security/security.xml',
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
