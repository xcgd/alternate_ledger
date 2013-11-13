# -*- coding: utf-8 -*-

# This file copies (and appropriately renames):
# - The account_move provided by the account module.
# - account_move modifications provided by the account_streamline module.
# account_streamline changes are marked with and "account_streamline" comment.

import logging
from lxml import etree

from openerp.osv import fields, osv
from openerp.tools.translate import _

import openerp.addons.decimal_precision as dp
import yaml

_logger = logging.getLogger(__name__)


class alternate_ledger_move(osv.osv):
    _name = "alternate_ledger.move"
    _description = "Account Entry"
    _order = 'id desc'

    def alternate_ledger_move_prepare(
        self, cr, uid, journal_id, date=False,
        ref='', company_id=False, context=None
    ):
        """Prepares and returns a dictionary of values, ready to be passed
        to create() based on the parameters received.
        """
        if not date:
            date = fields.date.today()

        period_obj = self.pool.get('account.period')

        if not company_id:
            user = self.pool.get(
                'res.users'
            ).browse(
                cr, uid, uid, context=context
            )

            company_id = user.company_id.id

        if context is None:
            context = {}

        # put the company in context to find the good period
        ctx = context.copy()
        ctx.update(
            {
                'company_id': company_id,
                'account_period_prefer_normal': True,
            }
        )

        return {
            'journal_id': journal_id,
            'date': date,
            'period_id': period_obj.find(cr, uid, date, context=ctx)[0],
            'ref': ref,
            'company_id': company_id,
        }

    def name_search(self, cr, user, name,
                    args=None, operator='ilike',
                    context=None, limit=80
                    ):
        """Returns a list of tupples containing id, name, as internally
        it is called {def name_get}
        result format: {[(id, name), (id, name), ...]}

        @param cr: A database cursor
        @param user: ID of the user currently logged in
        @param name: name to search
        @param args: other arguments
        @param operator: default operator is 'ilike', it can be changed
        @param context: context arguments, like lang, time zone
        @param limit: Returns first 'n' ids of complete result, default is 80.

        @return: Returns a list of tuples containing id and name
        """
        ids = []

        if not args:
            args = []

        if name:
            search_args = [('name', 'ilike', name)] + args

            ids += self.search(
                cr, user, search_args, limit=limit, context=context
            )

        if not ids and name and type(name) == int:
            search_args = [('id', '=', name)] + args

            ids += self.search(
                cr, user, search_args, limit=limit, context=context
            )

        if not ids:
            ids += self.search(cr, user, args, limit=limit, context=context)

        return self.name_get(cr, user, ids, context=context)

    def name_get(self, cursor, user, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]

        if not ids:
            return []

        res = []

        data_move = self.pool.get(
            'alternate_ledger.move'
        ).browse(
            cursor, user, ids, context=context
        )

        for move in data_move:
            if move.state == 'draft':
                name = '*' + str(move.id)
            else:
                name = move.name
            res.append((move.id, name))
        return res

    def _get_period(self, cr, uid, context=None):
        ctx = dict(context or {}, account_period_prefer_normal=True)
        period_ids = self.pool.get('account.period').find(cr, uid, context=ctx)
        return period_ids[0]

    def _amount_compute(self, cr, uid, ids, name, args, context, where=''):
        if not ids:
            return {}

        cr.execute('SELECT move_id, SUM(debit) '
                   'FROM alternate_ledger_move_line '
                   'WHERE move_id IN %s '
                   'GROUP BY move_id', (tuple(ids),)
                   )

        result = dict(cr.fetchall())

        for id in ids:
            result.setdefault(id, 0.0)

        return result

    def _search_amount(self, cr, uid, obj, name, args, context):
        ids = set()
        for cond in args:
            amount = cond[2]
            if isinstance(cond[2], (list, tuple)):
                if cond[1] in ['in', 'not in']:
                    amount = tuple(cond[2])
                else:
                    continue
            else:
                if cond[1] in [
                    '=like',
                    'like',
                    'not like',
                    'ilike',
                    'not ilike',
                    'in',
                    'not in',
                    'child_of',
                ]:
                    continue

            cr.execute(
                "select move_id from alternate_ledger_move_line "
                "group by move_id having sum(debit) %s %%s" % (cond[1]),
                (amount,)
            )
            res_ids = set(id[0] for id in cr.fetchall())
            ids = ids and (ids & res_ids) or res_ids

        if ids:
            return [('id', 'in', tuple(ids))]

        return [('id', '=', '0')]

    _columns = {
        'name': fields.char('Number', size=64, required=True),
        'ref': fields.char('Reference', size=64),
        'period_id': fields.many2one(
            'account.period',
            'Period',
            required=True,
            states={'posted': [('readonly', True)]}
        ),
        'journal_id': fields.many2one(
            'account.journal',
            'Journal',
            required=True,
            states={'posted': [('readonly', True)]}
        ),
        'state': fields.selection(
            [('draft', 'Unposted'),
             ('posted', 'Posted')],
            'Status',
            required=True,
            readonly=True,
            help="""All manually created new journal entries
                    are usually in the status \'Unposted\',
                    but you can set the option to skip that
                    status on the related journal. In that
                    case, they will behave as journal entries
                    automatically created by the system on document
                    validation (invoices, bank statements...)
                    and will be created in \'Posted\' status."""
        ),
        'line_id': fields.one2many(
            'alternate_ledger.move.line',
            'move_id',
            'Entries',
            states={'posted': [('readonly', True)]}
        ),
        'to_check': fields.boolean(
            'To Review',
            help="""Check this box if you are unsure of that
                    journal entry and if you want to note it
                    as \'to be reviewed\' by an accounting expert."""
        ),
        'partner_id': fields.related(
            'line_id',
            'partner_id',
            type="many2one",
            relation="res.partner",
            string="Partner",
            store=True
        ),
        'amount': fields.function(
            _amount_compute,
            string='Amount',
            digits_compute=dp.get_precision('Account'),
            type='float',
            fnct_search=_search_amount
        ),
        'date': fields.date(
            'Date',
            required=True,
            states={'posted': [('readonly', True)]},
            select=True
        ),
        'narration': fields.text('Internal Note'),
        'company_id': fields.related(
            'journal_id',
            'company_id',
            type='many2one',
            relation='res.company',
            string='Company',
            store=True,
            readonly=True
        ),
        'balance': fields.float(
            'balance',
            digits_compute=dp.get_precision('Account'),
            help="""This is a field only used for internal purpose
                    and shouldn't be displayed"""
        ),
        'ledger_id': fields.many2one(
            'alternate_ledger.ledger_type',
            _('Ledger Type'),
        ),
    }

    _defaults = {
        'name': '/',
        'state': 'draft',
        'period_id': _get_period,
        'date': fields.date.context_today,
        'company_id': lambda self, cr, uid, c: self.pool.get(
            'res.users').browse(cr, uid, uid, c).company_id.id,
    }

    def _check_centralisation(self, cursor, user, ids, context=None):
        for move in self.browse(cursor, user, ids, context=context):
            if move.journal_id.centralisation:
                move_ids = self.search(cursor, user, [
                    ('period_id', '=', move.period_id.id),
                    ('journal_id', '=', move.journal_id.id),
                ])
                if len(move_ids) > 1:
                    return False
        return True

    _constraints = [
        (
            _check_centralisation,
            'You cannot create more than one move per period '
            'on a centralized journal.',
            ['journal_id']
        ),
    ]

    def post_(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        invoice = context.get('invoice', False)
        valid_moves = self.validate(cr, uid, ids, context)

        if not valid_moves:
            raise osv.except_osv(
                _('Error!'),
                _('You cannot validate a non-balanced entry.\n'
                  'Make sure you have configured payment terms properly.\n'
                  'The latest payment term line should be '
                  'of the "Balance" type.'
                  )
            )
        obj_sequence = self.pool.get('ir.sequence')
        for move in self.browse(cr, uid, valid_moves, context=context):
            if move.name == '/':
                new_name = False
                journal = move.journal_id

                if invoice and invoice.internal_number:
                    new_name = invoice.internal_number
                else:
                    if journal.sequence_id:
                        c = {'fiscalyear_id': move.period_id.fiscalyear_id.id}
                        new_name = obj_sequence.next_by_id(
                            cr, uid, journal.sequence_id.id, c
                        )
                    else:
                        raise osv.except_osv(
                            _('Error!'),
                            _('Please define a sequence on the journal.')
                        )

                if new_name:
                    self.write(
                        cr, uid, [move.id],
                        {'name': new_name}
                    )

        cr.execute(
            'UPDATE alternate_ledger_move '
            'SET state=%s '
            'WHERE id IN %s',
            ('posted', tuple(valid_moves),)
        )
        return True

    # account_streamline
    def _analysis_control(self, cr, uid, ids, context=None):
        """This controls the account.move.line analysis dimensions settings
        set on account.account
        It will perform this only when attempting to post a complete move and
        will compile all errors coming from move lines in a single message
        """
        # move_dict = {}
        lines = []

        ans_obj = self.pool.get('analytic.structure')
        ans_ids = ans_obj.search(cr, uid,
                                 [('model_name', '=', 'account_move_line')],
                                 context=context)
        ans_br = ans_obj.browse(cr, uid, ans_ids, context=context)
        ans_dict = dict()
        for ans in ans_br:
            ans_dict[ans.ordering] = ans.nd_id.name

        for move in self.browse(cr, uid, ids, context=context):
            # line_dict = []
            for aml in move.line_id:
                dim_list = []
                if aml.account_id.t1_ctl == '1' and not aml.a1_id:
                    dim_list.append(ans_dict.get('1', 'A1').encode('utf8'))
                if aml.account_id.t2_ctl == '1' and not aml.a2_id:
                    dim_list.append(ans_dict.get('2', 'A2').encode('utf8'))
                if aml.account_id.t3_ctl == '1' and not aml.a3_id:
                    dim_list.append((ans_dict.get('3', 'A3').encode('utf8')))
                if aml.account_id.t4_ctl == '1' and not aml.a4_id:
                    dim_list.append((ans_dict.get('4', 'A4').encode('utf8')))
                if aml.account_id.t5_ctl == '1' and not aml.a5_id:
                    dim_list.append((ans_dict.get('5', 'A5').encode('utf8')))
                if dim_list:
                    # line_dict[aml.name.encode('utf8')] = dim_list
                    tmp = [aml.name.encode('utf8')]
                    tmp.append(dim_list)
                    lines += tmp
            # if lines:
                # move_dict[move.ref.encode('utf8')] = line_dict

        if lines:
            msg_analysis = _("Unable to post! "
                             "The following analysis codes are mandatory:")
            msg_analysis += '\n'
            msg_analysis += yaml.dump(lines)

            raise osv.except_osv(_('Error!'), msg_analysis)

    # account_streamline
    def post(self, cr, uid, ids, context=None):
        """override the post method so all lines can be check against
        analysis controls
        """
        self._analysis_control(cr, uid, ids, context=context)

        return self.post_(cr, uid, ids, context=context)

    def button_validate(self, cursor, user, ids, context=None):
        for move in self.browse(cursor, user, ids, context=context):
            # check that all accounts have the same topmost ancestor
            top_common = None
            for line in move.line_id:
                account = line.account_id
                top_account = account
                while top_account.parent_id:
                    top_account = top_account.parent_id
                if not top_common:
                    top_common = top_account
                elif top_account.id != top_common.id:
                    raise osv.except_osv(
                        _('Error!'),
                        _('You cannot validate this journal entry because '
                          'account "%s" does not belong to chart of accounts '
                          '"%s".') % (account.name, top_common.name))

        return self.post(cursor, user, ids, context=context)

    def button_cancel(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context=context):
            if not line.journal_id.update_posted:
                raise osv.except_osv(
                    _('Error!'),
                    _('You cannot modify a posted entry of this journal.\n'
                      'First you should set the journal to allow '
                      'cancelling entries.')
                )
        if ids:
            cr.execute(
                'UPDATE alternate_ledger_move '
                'SET state=%s '
                'WHERE id IN %s', ('draft', tuple(ids),)
            )

        return True

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        c = context.copy()
        c['novalidate'] = True
        result = super(
            alternate_ledger_move, self
        ).write(cr, uid, ids, vals, c)

        self.validate(cr, uid, ids, context=context)
        return result

    #
    # TODO: Check if period is closed !
    #
    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if 'line_id' in vals and context.get('copy'):
            for l in vals['line_id']:
                if not l[0]:
                    l[2].update({
                        'reconcile_id': False,
                        'reconcile_partial_id': False,
                        'analytic_lines': False,
                        'invoice': False,
                        'ref': False,
                        'balance': False,
                        'account_tax_id': False,
                        'statement_id': False,
                    })

            if 'journal_id' in vals and vals.get('journal_id', False):
                for l in vals['line_id']:
                    if not l[0]:
                        l[2]['journal_id'] = vals['journal_id']
                context['journal_id'] = vals['journal_id']
            if 'period_id' in vals:
                for l in vals['line_id']:
                    if not l[0]:
                        l[2]['period_id'] = vals['period_id']
                context['period_id'] = vals['period_id']
            else:
                default_period = self._get_period(cr, uid, context)
                for l in vals['line_id']:
                    if not l[0]:
                        l[2]['period_id'] = default_period
                context['period_id'] = default_period

        if 'line_id' in vals:
            c = context.copy()
            c['novalidate'] = True
            c['period_id'] = vals[
                'period_id'
            ] if 'period_id' in vals else self._get_period(cr, uid, context)

            c['journal_id'] = vals['journal_id']

            if 'date' in vals:
                c['date'] = vals['date']

            result = super(
                alternate_ledger_move, self
            ).create(
                cr, uid, vals, c
            )
            self.validate(cr, uid, [result], context)

        else:
            result = super(
                alternate_ledger_move, self
            ).create(
                cr, uid, vals, context
            )

        return result

    def copy(self, cr, uid, id, default=None, context=None):
        default = {} if default is None else default.copy()
        context = {} if context is None else context.copy()
        default.update(
            {
                'state': 'draft',
                'ref': False,
                'name': '/',
            }
        )
        context.update({
            'copy': True
        })
        return super(
            alternate_ledger_move, self
        ).copy(cr, uid, id, default, context)

    def unlink(self, cr, uid, ids, context=None, check=True):
        if context is None:
            context = {}
        toremove = []
        obj_move_line = self.pool.get('alternate_ledger.move.line')
        for move in self.browse(cr, uid, ids, context=context):
            if move['state'] != 'draft':
                raise osv.except_osv(
                    _('User Error!'),
                    _('You cannot delete a posted '
                      'journal entry "%s".') % move['name'])

            for line in move.line_id:
                if line.invoice:
                    raise osv.except_osv(
                        _('User Error!'),
                        _("Move cannot be deleted if linked "
                          "to an invoice. (Invoice: %s - Move ID:%s)"
                          ) % (line.invoice.number, move.name)
                    )

            line_ids = map(lambda x: x.id, move.line_id)
            context['journal_id'] = move.journal_id.id
            context['period_id'] = move.period_id.id
            obj_move_line._update_check(cr, uid, line_ids, context)
            obj_move_line.unlink(cr, uid, line_ids, context=context)
            toremove.append(move.id)

        result = super(
            alternate_ledger_move, self
        ).unlink(cr, uid, toremove, context)
        return result

    def _compute_balance(self, cr, uid, id, context=None):
        move = self.browse(cr, uid, id, context=context)
        amount = 0
        for line in move.line_id:
            amount += (line.debit - line.credit)
        return amount

    def _centralise(self, cr, uid, move, mode, context=None):
        # to prevent sql injection
        assert mode in ('debit', 'credit'), 'Invalid Mode'
        currency_obj = self.pool.get('res.currency')
        if context is None:
            context = {}

        if mode == 'credit':
            account_id = move.journal_id.default_debit_account_id.id
            mode2 = 'debit'
            if not account_id:
                raise osv.except_osv(
                    _('User Error!'),
                    _('There is no default debit account defined\n'
                      'on journal "%s".') % move.journal_id.name)
        else:
            account_id = move.journal_id.default_credit_account_id.id
            mode2 = 'credit'
            if not account_id:
                raise osv.except_osv(
                    _('User Error!'),
                    _('There is no default credit account defined\n'
                      'on journal "%s".') % move.journal_id.name)

        # find the first line of this move with the current mode
        # or create it if it doesn't exist
        cr.execute(
            'select id from alternate_ledger_move_line '
            'where move_id=%s and centralisation=%s limit 1', (move.id, mode)
        )
        res = cr.fetchone()
        if res:
            line_id = res[0]
        else:
            context.update(
                {
                    'journal_id': move.journal_id.id,
                    'period_id': move.period_id.id,
                }
            )

            aaml_osv = self.pool.get('alternate_ledger.move.line')

            line_id = aaml_osv.create(
                cr,
                uid,
                {
                    'name': _(mode.capitalize() + ' Centralisation'),
                    'centralisation': mode,
                    'partner_id': False,
                    'account_id': account_id,
                    'move_id': move.id,
                    'journal_id': move.journal_id.id,
                    'period_id': move.period_id.id,
                    'date': move.period_id.date_stop,
                    'debit': 0.0,
                    'credit': 0.0,
                },
                context
            )

        # find the first line of this move with the other mode
        # so that we can exclude it from our calculation
        cr.execute(
            'select id from alternate_ledger_move_line '
            'where move_id=%s and centralisation=%s limit 1', (move.id, mode2)
        )
        res = cr.fetchone()
        if res:
            line_id2 = res[0]
        else:
            line_id2 = 0

        cr.execute(
            'SELECT SUM(%s) FROM alternate_ledger_move_line '
            'WHERE move_id=%%s AND id!=%%s' % (mode,), (move.id, line_id2)
        )
        result = cr.fetchone()[0] or 0.0
        cr.execute(
            'update alternate_ledger_move_line set'
            ' ' + mode2 + '=%s where id=%s', (result, line_id)
        )

        # adjust also the amount in currency if needed
        cr.execute(
            "select currency_id, sum(amount_currency) "
            "as amount_currency from alternate_ledger_move_line "
            "where move_id = %s and currency_id is not null "
            "group by currency_id", (move.id,)
        )
        for row in cr.dictfetchall():
            currency_id = currency_obj.browse(
                cr, uid, row['currency_id'], context=context)

            if not currency_obj.is_zero(
                cr, uid, currency_id, row['amount_currency']
            ):
                amount_currency = row['amount_currency'] * -1

                account_id = amount_currency > 0 and \
                    move.journal_id.default_debit_account_id.id or \
                    move.journal_id.default_credit_account_id.id

                cr.execute(
                    "select id from alternate_ledger_move_line "
                    "where move_id=%s and centralisation='currency' "
                    "and currency_id = %slimit 1",
                    (move.id, row['currency_id'])
                )
                res = cr.fetchone()
                if res:
                    cr.execute(
                        'update alternate_ledger_move_line '
                        'set amount_currency=%s , account_id=%s where id=%s',
                        (amount_currency, account_id, res[0])
                    )
                else:
                    context.update(
                        {
                            'journal_id': move.journal_id.id,
                            'period_id': move.period_id.id
                        }
                    )
                    aaml_osv = self.pool.get('alternate_ledger.move.line')
                    line_id = aaml_osv.create(cr, uid, {
                        'name': _('Currency Adjustment'),
                        'centralisation': 'currency',
                        'partner_id': False,
                        'account_id': account_id,
                        'move_id': move.id,
                        'journal_id': move.journal_id.id,
                        'period_id': move.period_id.id,
                        'date': move.period_id.date_stop,
                        'debit': 0.0,
                        'credit': 0.0,
                        'currency_id': row['currency_id'],
                        'amount_currency': amount_currency,
                    }, context)

        return True

    #
    # Validate a balanced move. If it is a centralised journal, create a move.
    #
    def validate(self, cr, uid, ids, context=None):
        if context and ('__last_update' in context):
            del context['__last_update']

        # Maintains a list of moves which can be responsible
        #to create analytic entries
        valid_moves = []
        obj_analytic_line = self.pool.get('account.analytic.line')
        obj_move_line = self.pool.get('alternate_ledger.move.line')
        for move in self.browse(cr, uid, ids, context):
            # Unlink old analytic lines on move_lines
            for obj_line in move.line_id:
                for obj in obj_line.analytic_lines:
                    obj_analytic_line.unlink(cr, uid, obj.id)

            journal = move.journal_id
            amount = 0
            line_ids = []
            line_draft_ids = []
            company_id = None
            for line in move.line_id:
                amount += line.debit - line.credit
                line_ids.append(line.id)
                if line.state == 'draft':
                    line_draft_ids.append(line.id)

                if not company_id:
                    company_id = line.account_id.company_id.id
                if not company_id == line.account_id.company_id.id:
                    raise osv.except_osv(
                        _('Error!'),
                        _("Cannot create moves for different companies.")
                    )

                if line.account_id.currency_id and line.currency_id:
                    account = line.account_id
                    if account.currency_id.id != line.currency_id.id \
                       and (
                           account.currency_id.id !=
                           account.company_id.currency_id.id
                       ):
                        # TODO: this message is False and will fail
                        # horribly!!!!
                        raise osv.except_osv(
                            _('Error!'),
                            _("Cannot create move with currency "
                              "different from .."
                              ) % (line.account_id.code, line.account_id.name)
                        )

            valid_moves.append(move)

            # Check whether the move lines are confirmed

            if not line_draft_ids:
                continue
            # Update the move lines (set them as valid)

            obj_move_line.write(cr, uid, line_draft_ids, {
                'state': 'valid'
            }, context, check=False)

            account = {}
            account2 = {}

            if journal.type in ('purchase', 'sale'):
                for line in move.line_id:
                    code = amount = 0
                    key = (line.account_id.id, line.tax_code_id.id)
                    if key in account2:
                        code = account2[key][0]
                        amount = account2[key][1] * (line.debit + line.credit)
                    elif line.account_id.id in account:
                        code = account[line.account_id.id][0]
                        amount = account[line.account_id.id][1] * (
                            line.debit + line.credit)
                    if (code or amount) and not (
                        line.tax_code_id or line.tax_amount
                    ):
                        obj_move_line.write(cr, uid, [line.id], {
                            'tax_code_id': code,
                            'tax_amount': amount
                        }, context, check=False)
            if journal.centralisation:
                # If the move is not balanced, it must be centralised...

                # Add to the list of valid moves
                # (analytic lines will be created later for valid moves)
                valid_moves.append(move)

                #
                # Update the move lines (set them as valid)
                #
                self._centralise(cr, uid, move, 'debit', context=context)
                self._centralise(cr, uid, move, 'credit', context=context)
                obj_move_line.write(cr, uid, line_draft_ids, {
                    'state': 'valid'
                }, context, check=False)
            else:
                # We can't validate it (it's unbalanced)
                # Setting the lines as draft
                obj_move_line.write(cr, uid, line_ids, {
                    'state': 'draft'
                }, context, check=False)
        # Create analytic lines for the valid moves
        for record in valid_moves:
            obj_move_line.create_analytic_lines(
                cr, uid, [line.id for line in record.line_id], context)

        valid_moves = [move.id for move in valid_moves]
        return len(valid_moves) > 0 and valid_moves or False

    # account_streamline
    def fields_view_get(self, cr, uid, view_id=None, view_type='form',
                        context=None, toolbar=False, submenu=False):
        """We display analysis codes on the account.move form inserting
        them in the one2many field containing account move lines
        """
        if context is None:
            context = {}
        res = super(alternate_ledger_move,
                    self).fields_view_get(cr, uid, view_id=view_id,
                                          view_type=view_type,
                                          context=context,
                                          toolbar=toolbar,
                                          submenu=False)
        ans_obj = self.pool.get('analytic.structure')

        # display analysis codes only when present on a related structure,
        # with dimension name as label
        ans_ids = ans_obj.search(cr, uid,
                                 [('model_name', '=', 'account_move_line')],
                                 context=context)
        ans_br = ans_obj.browse(cr, uid, ans_ids, context=context)
        ans_dict = dict()
        for ans in ans_br:
            ans_dict[ans.ordering] = ans.nd_id.name
        if 'fields' in res and 'line_id' in res['fields']:
            doc = etree.XML(res['fields']['line_id']['views']['tree']['arch'])
            line_fields = res['fields']['line_id']['views']['tree']['fields']
            if 'a1_id' in line_fields:
                line_fields['a1_id']['string'] = ans_dict.get('1', 'A1')
                doc.xpath("//field[@name='a1_id']")[0].\
                    set('modifiers', '{"tree_invisible": %s}' %
                        str(not '1' in ans_dict).lower())
            if 'a2_id' in line_fields:
                line_fields['a2_id']['string'] = ans_dict.get('2', 'A2')
                doc.xpath("//field[@name='a2_id']")[0].\
                    set('modifiers', '{"tree_invisible": %s}' %
                        str(not '2' in ans_dict).lower())
            if 'a3_id' in line_fields:
                line_fields['a3_id']['string'] = ans_dict.get('3', 'A3')
                doc.xpath("//field[@name='a3_id']")[0].\
                    set('modifiers', '{"tree_invisible": %s}' %
                        str(not '3' in ans_dict).lower())
            if 'a4_id' in line_fields:
                line_fields['a4_id']['string'] = ans_dict.get('4', 'A4')
                doc.xpath("//field[@name='a4_id']")[0].\
                    set('modifiers', '{"tree_invisible": %s}' %
                        str(not '4' in ans_dict).lower())
            if 'a5_id' in line_fields:
                line_fields['a5_id']['string'] = ans_dict.get('5', 'A5')
                doc.xpath("//field[@name='a5_id']")[0].\
                    set('modifiers', '{"tree_invisible": %s}' %
                        str(not '5' in ans_dict).lower())
            res['fields']['line_id'][
                'views']['tree']['arch'] = etree.tostring(doc)
        return res

alternate_ledger_move()


class alternate_ledger_move_reconcile(osv.osv):
    _name = "alternate_ledger.move.reconcile"
    _description = "Account Reconciliation"
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'type': fields.char('Type', size=16, required=True),
        'line_id': fields.one2many(
            'alternate_ledger.move.line',
            'reconcile_id',
            'Entry Lines'
        ),
        'line_partial_ids': fields.one2many(
            'alternate_ledger.move.line',
            'reconcile_partial_id',
            'Partial Entry lines'
        ),
        'create_date': fields.date('Creation date', readonly=True),
        'opening_reconciliation': fields.boolean(
            'Opening Entries Reconciliation',
            help="Is this reconciliation produced "
            "by the opening of a new fiscal year ?."
        ),
    }
    _defaults = {
        'name': lambda self, cr, uid, ctx = None: self.pool.get(
            'ir.sequence').get(
                cr, uid, 'account.reconcile', context=ctx) or '/',
    }

    # You cannot unlink a reconciliation if it is a opening_reconciliation one,
    # you should use the generate opening entries wizard for that
    def unlink(self, cr, uid, ids, context=None):
        for move_rec in self.browse(cr, uid, ids, context=context):
            if move_rec.opening_reconciliation:
                raise osv.except_osv(
                    _('Error!'),
                    _('You cannot unreconcile journal '
                      'items if they has been generated '
                      'by the opening/closing fiscal year process.')
                )
        return super(
            alternate_ledger_move_reconcile, self
        ).unlink(cr, uid, ids, context=context)

    # Look in the line_id and line_partial_ids to ensure the partner
    # is the same or empty on all lines.
    # We allow that only for opening/closing period
    def _check_same_partner(self, cr, uid, ids, context=None):
        for reconcile in self.browse(cr, uid, ids, context=context):
            move_lines = []
            if not reconcile.opening_reconciliation:
                if reconcile.line_id:
                    first_partner = reconcile.line_id[0].partner_id.id
                    move_lines = reconcile.line_id
                elif reconcile.line_partial_ids:
                    first_partner = reconcile.line_partial_ids[0].partner_id.id
                    move_lines = reconcile.line_partial_ids

                if any(
                    [
                        (line.account_id.type in ('receivable', 'payable')
                         and line.partner_id.id != first_partner
                         ) for line in move_lines
                    ]
                ):
                    return False
        return True

    _constraints = [
        (
            _check_same_partner,
            'You can only reconcile journal items with the same partner.',
            ['line_id']
        ),
    ]

    def reconcile_partial_check(self, cr, uid, ids, type='auto', context=None):
        total = 0.0
        for rec in self.browse(cr, uid, ids, context=context):
            for line in rec.line_partial_ids:
                if line.account_id.currency_id:
                    total += line.amount_currency
                else:
                    total += (line.debit or 0.0) - (line.credit or 0.0)
        if not total:
            aaml_osv = self.pool.get('alternate_ledger.move.line')
            aaml_osv.write(
                cr, uid,
                map(lambda x: x.id, rec.line_partial_ids),
                {'reconcile_id': rec.id}
            )
        return True

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        result = []
        for r in self.browse(cr, uid, ids, context=context):
            total = reduce(
                lambda y, t: (t.debit or 0.0) - (t.credit or 0.0) + y,
                r.line_partial_ids,
                0.0
            )
            if total:
                name = '%s (%.2f)' % (r.name, total)
                result.append((r.id, name))
            else:
                result.append((r.id, r.name))
        return result

alternate_ledger_move_reconcile()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
