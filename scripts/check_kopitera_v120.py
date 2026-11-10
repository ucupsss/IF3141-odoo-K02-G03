"""Uji fitur 17.0.1.2.0 lewat Odoo shell. Semua perubahan dibatalkan (rollback) di akhir.

Cakupan: perbandingan gramasi + log audit (UC-04/07), pemulihan versi (UC-08), akun dan peran (UC-09),
laporan (UC-11), notifikasi (UC-12), migrasi Excel (UC-13), dan sinkronisasi BoM Manufacturing.
"""
import base64
import io
from datetime import timedelta

import xlsxwriter
from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError

passed = []


def expect(label, condition):
    assert condition, label
    passed.append(label)


def denied(label, fn):
    try:
        with env.cr.savepoint():
            fn()
    except (AccessError, UserError, ValidationError):
        passed.append(label)
        return
    raise AssertionError('Unexpectedly allowed: ' + label)


def user(key):
    return env['res.users'].search([('login', '=', key + '.kopitera')], limit=1)


def run_recipe(recipe, author, reviewer, manager, note='Uji'):
    recipe.with_user(author).action_submit()
    recipe.with_user(reviewer).write({'review_note': note})
    recipe.with_user(reviewer).action_review()
    recipe.with_user(manager).write({'decision_note': note, 'release_date': fields.Date.today()})
    recipe.with_user(manager).action_approve()
    recipe.with_user(manager).action_release()


try:
    author, reviewer, manager = user('headbar'), user('reviewerbar'), user('manager')
    staff, floor, mod, kitchen_head = user('stafbar'), user('headfloor'), user('mod'), user('headkitchen')
    assert all([author, reviewer, manager, staff, floor, mod, kitchen_head]), 'Akun uji belum lengkap'
    Recipe, Notification, Log = env['kopitera.recipe'], env['kopitera.notification'], env['kopitera.audit.log']
    menu = env.ref('kopitera_master.menu_kopi_susu')
    v_old = menu.current_recipe_id
    sugar = env.ref('kopitera_master.ingredient_sugar')
    milk = env.ref('kopitera_master.ingredient_milk')

    # ---------------------------------------------------------- UC-04/07 perbandingan + audit
    draft = Recipe.browse(menu.with_user(author).action_propose_recipe()['res_id'])
    draft.with_user(author).write({'reason': 'Uji v1.2.0'})
    line = draft.line_ids.filtered(lambda l: l.ingredient_id == sugar)
    line.with_user(author).write({'quantity': 15})
    draft.line_ids.filtered(lambda l: l.ingredient_id == milk).with_user(author).unlink()
    html = str(draft.with_user(reviewer).comparison_html)
    expect('comparison shows changed quantity', 'Sirup Gula Aren' in html and 'Berkurang' in html and '-5' in html)
    expect('comparison shows removed ingredient', 'Susu Cair' in html and 'Dihapus' in html)
    expect('comparison base is current version', str(v_old.version) in draft.comparison_label)

    draft.with_user(author).action_submit()
    expect('submit writes audit log', Log.search_count([('recipe_id', '=', draft.id), ('action', '=', 'submit')]) == 1)
    expect('submit notifies Head Bar reviewer only',
           set(Notification.sudo().search([('recipe_id', '=', draft.id), ('kind', '=', 'review')]).user_id.ids) == {reviewer.id})
    expect('kitchen head not notified about bar recipe',
           not Notification.sudo().search_count([('recipe_id', '=', draft.id), ('user_id', '=', kitchen_head.id)]))
    denied('audit log cannot be forged by user', lambda: Log.with_user(manager).create({'action': 'submit', 'object_type': 'recipe', 'user_id': manager.id}))
    first_log = Log.search([('recipe_id', '=', draft.id)], limit=1)
    denied('audit log cannot be edited', lambda: first_log.write({'note': 'ubah'}))
    denied('audit log cannot be deleted', lambda: first_log.sudo().unlink())
    denied('staff cannot read audit log', lambda: first_log.with_user(staff).read(['note']))
    expect('kitchen head cannot see bar audit log', not Log.with_user(kitchen_head).search_count([('id', '=', first_log.id)]))

    draft.with_user(reviewer).write({'review_note': 'Takaran sesuai'})
    draft.with_user(reviewer).action_review()
    expect('review notifies manager', Notification.sudo().search_count([('recipe_id', '=', draft.id), ('kind', '=', 'approval'), ('user_id', '=', manager.id)]) == 1)
    note = Notification.with_user(reviewer).search([('recipe_id', '=', draft.id)], limit=1)
    expect('recipient sees own notification', bool(note))
    denied('other user cannot read reviewer notification', lambda: note.with_user(manager).read(['name']))
    denied('notification text cannot be edited', lambda: note.with_user(reviewer).write({'name': 'Ubah'}))
    note.with_user(reviewer).action_mark_read()
    expect('notification marked read', note.is_read)

    draft.with_user(manager).write({'decision_note': 'Setuju', 'release_date': fields.Date.today()})
    draft.with_user(manager).action_approve()
    expect('approve notifies author', Notification.sudo().search_count([('recipe_id', '=', draft.id), ('kind', '=', 'approved'), ('user_id', '=', author.id)]) == 1)
    old_bom = v_old.sudo().bom_id
    draft.with_user(manager).action_release()
    expect('release links previous version', draft.previous_recipe_id == v_old and v_old.state == 'archived')
    release_receivers = set(Notification.sudo().search([('recipe_id', '=', draft.id), ('kind', '=', 'release')]).user_id.ids)
    expect('release notifies author and Head Floor', {author.id, floor.id} <= release_receivers)
    expect('release not sent to staff or MoD', not ({staff.id, mod.id} & release_receivers))
    release_log = Log.search([('recipe_id', '=', draft.id), ('action', '=', 'release')])
    expect('release log keeps before/after composition', 'Susu Cair' in release_log.before_value and 'Susu Cair' not in release_log.after_value)
    expect('published comparison against previous version', 'Dihapus' in str(draft.with_user(manager).comparison_html))

    # ---------------------------------------------------------- BoM Manufacturing
    new_bom = draft.sudo().bom_id
    expect('release creates active BoM', new_bom.active and len(new_bom.bom_line_ids) == len(draft.line_ids))
    expect('old BoM archived', bool(old_bom) and not old_bom.active)
    sugar_line = new_bom.bom_line_ids.filtered(lambda l: l.product_id == sugar.sudo().product_id)
    expect('BoM quantity and ml unit match recipe', sugar_line.product_qty == 15 and sugar_line.product_uom_id == env.ref('kopitera_master.uom_ml'))

    # ---------------------------------------------------------- UC-08 pemulihan versi
    Wizard = env['kopitera.restore.wizard']
    denied('head cannot open restore', lambda: v_old.with_user(author).action_open_restore())
    denied('cannot restore current version', lambda: draft.with_user(manager).action_open_restore())
    denied('head cannot create restore wizard action', lambda: Wizard.with_user(author).create({'recipe_id': v_old.id, 'reason': 'x'}).action_confirm())
    denied('restored_from cannot be forged', lambda: Recipe.with_user(author).create({'menu_id': menu.id, 'restored_from_id': v_old.id}))
    wizard = Wizard.with_user(manager).create({'recipe_id': v_old.id, 'reason': 'Versi 2 keliru'})
    expect('restore preview compares current and target', 'Susu Cair' in str(wizard.preview_html) and wizard.current_version == draft.version)
    restore = Recipe.browse(wizard.action_confirm()['res_id'])
    expect('restore creates submitted proposal', restore.state == 'review' and restore.restored_from_id == v_old)
    expect('restore keeps current version live', menu.current_recipe_id == draft)
    expect('restore copies target composition', sorted(restore.line_ids.mapped('quantity')) == sorted(v_old.line_ids.mapped('quantity')))
    expect('restore logged', Log.search_count([('recipe_id', '=', restore.id), ('action', '=', 'restore')]) == 1)
    denied('second open restore rejected', lambda: Wizard.with_user(manager).create({'recipe_id': v_old.id, 'reason': 'lagi'}).action_confirm())
    restore.with_user(reviewer).write({'review_note': 'Kembali ke versi lama'})
    restore.with_user(reviewer).action_review()
    restore.with_user(manager).write({'decision_note': 'Setuju pemulihan', 'release_date': fields.Date.today()})
    restore.with_user(manager).action_approve()
    restore.with_user(manager).action_release()
    expect('restore becomes new version number', restore.state == 'published' and restore.version == draft.version + 1)
    expect('restored history intact', draft.state == 'archived' and v_old.state == 'archived')

    # ---------------------------------------------------------- UC-09 akun dan peran
    Account = env['kopitera.account']
    denied('head cannot read accounts', lambda: Account.with_user(author).search([]))
    denied('password required', lambda: Account.with_user(manager).create({'name': 'Uji', 'login': 'uji1.kopitera', 'role': 'staf_bar'}))
    acc = Account.with_user(manager).create({'name': 'Staf Uji', 'login': 'stafuji.kopitera', 'role': 'staf_bar',
                                             'branch': 'dago', 'new_password': 'PasswordUji123'})
    expect('account creates restricted user', acc.user_id.has_group('kopitera_master.group_bar')
           and not acc.user_id.has_group('kopitera_master.group_editor') and not acc.user_id.has_group('base.group_system'))
    expect('job title follows role', acc.job_title == 'Staf Bar (JB-11)')
    acc.with_user(manager).write({'role': 'head_kitchen'})
    expect('role change replaces groups', acc.user_id.has_group('kopitera_master.group_head_kitchen') and not acc.user_id.has_group('kopitera_master.group_bar'))
    acc.with_user(manager).action_deactivate()
    expect('deactivate disables login', acc.state == 'inactive' and not acc.user_id.active)
    acc.with_user(manager).action_activate()
    expect('reactivate account', acc.state == 'active' and acc.user_id.active)
    denied('manager cannot unlink account', lambda: acc.with_user(manager).unlink())
    denied('state cannot be forged', lambda: acc.with_user(manager).write({'state': 'inactive'}))
    own = Account.search([('user_id', '=', manager.id)])
    denied('manager cannot deactivate self', lambda: own.with_user(manager).action_deactivate())
    denied('manager cannot change own role', lambda: own.with_user(manager).write({'role': 'staf_bar'}))
    denied('cannot attach existing admin user', lambda: Account.with_user(manager).create({'name': 'x', 'login': 'x', 'role': 'manager', 'user_id': env.ref('base.user_admin').id, 'new_password': 'PasswordUji123'}))
    denied('duplicate login rejected', lambda: Account.with_user(manager).create({'name': 'x', 'login': 'stafuji.kopitera', 'role': 'staf_bar', 'new_password': 'PasswordUji123'}))

    # ---------------------------------------------------------- UC-11 laporan
    Report = env['kopitera.report.wizard']
    bar_report = Report.with_user(author).create({'report_type': 'catalog'})
    names = [row[0] for row in bar_report._get_table()[1]]
    expect('Head Bar catalog only bar menus', 'Es Kopi Susu — Contoh' in names and 'Nasi Goreng — Contoh' not in names)
    floor_report = Report.with_user(floor).create({'report_type': 'recipe'})
    expect('Head Floor recipe sheet sees both divisions', {'Es Kopi Susu — Contoh', 'Nasi Goreng — Contoh'} <= {r[0] for r in floor_report._get_table()[1]})
    history = Report.with_user(manager).create({'report_type': 'history', 'history_action': 'release',
                                                'date_from': fields.Date.today(), 'date_to': fields.Date.today()})
    expect('history report filters releases', history._get_table()[1] and all(r[4] == 'Dirilis' for r in history._get_table()[1]))
    expect('preview rendered', '<table' in str(history.preview_html))
    action = history.with_user(manager).write({'output_format': 'xlsx'}) and history.with_user(manager).action_export()
    expect('xlsx export downloadable', action['type'] == 'ir.actions.act_url' and history.file_data and history.file_name.endswith('.xlsx'))
    denied('staff cannot open report wizard', lambda: Report.with_user(staff).create({'report_type': 'catalog'}))
    denied('MoD cannot open report wizard', lambda: Report.with_user(mod).create({'report_type': 'catalog'}))
    denied('invalid date range', lambda: Report.with_user(manager).create({'report_type': 'history', 'date_from': fields.Date.today(),
                                                                          'date_to': fields.Date.today() - timedelta(days=1)}).action_export())
    pdf, kind = env['ir.actions.report'].with_user(manager)._render_qweb_pdf('kopitera_master.action_report_kopitera', [floor_report.id])
    expect('PDF lembar resep dirender', kind == 'pdf' and pdf[:4] == b'%PDF')

    # ---------------------------------------------------------- UC-13 migrasi Excel
    buffer = io.BytesIO()
    book = xlsxwriter.Workbook(buffer, {'in_memory': True})
    def sheet(name, rows):
        ws = book.add_worksheet(name)
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                ws.write(r, c, value)
    sheet('Menu', [['Nama Menu', 'Divisi', 'Deskripsi', 'Alergen', 'Langkah Penyiapan'],
                   ['Matcha Latte Uji', 'bar', 'Uji migrasi', 'Susu', '1. Kocok matcha\n2. Tambah susu'],
                   ['Es Kopi Susu — Contoh', 'bar', 'duplikat', '', ''],
                   ['Menu Salah', 'dapur', '', '', '']])
    sheet('Bahan', [['Nama Bahan', 'Satuan', 'Area Penggunaan'], ['Bubuk Matcha Uji', 'g', 'bar'],
                    ['Bahan Salah', 'kg', 'bar']])
    sheet('Resep', [['Nama Menu', 'Nama Bahan', 'Takaran'], ['Matcha Latte Uji', 'Bubuk Matcha Uji', 5],
                    ['Matcha Latte Uji', 'Susu Cair', 150], ['Menu Tak Ada', 'Susu Cair', 10]])
    sheet('Akun', [['Nama', 'Login', 'Peran', 'Cabang'], ['Staf Migrasi', 'stafmigrasi.kopitera', 'staf_kitchen', 'dago']])
    book.close()
    Import = env['kopitera.import.wizard']
    denied('manager cannot run migration', lambda: Import.with_user(manager).create({'file_data': base64.b64encode(buffer.getvalue()), 'file_name': 'a.xlsx'}).action_preview())
    dev = env.ref('base.user_admin')
    wiz = Import.with_user(dev).create({'file_data': base64.b64encode(buffer.getvalue()), 'file_name': 'uji-migrasi.xlsx'})
    menu_count = env['kopitera.menu'].search_count([])
    wiz.action_preview()
    expect('preview does not write data', env['kopitera.menu'].search_count([]) == menu_count and wiz.state == 'preview')
    expect('preview counts valid and invalid rows', wiz.valid_count == 5 and wiz.invalid_count == 4)
    wiz.action_import()
    matcha = env['kopitera.menu'].search([('name', '=', 'Matcha Latte Uji')])
    expect('import creates menu with published v1', matcha.current_recipe_id.state == 'published' and matcha.current_recipe_id.version == 1)
    expect('imported recipe has BoM', matcha.current_recipe_id.sudo().bom_id.active)
    expect('import log counts', wiz.log_id.success_count == 5 and wiz.log_id.failed_count == 4 and 'Menu Salah' not in wiz.log_id.summary)
    expect('import log lists failures', 'sudah terdaftar' in wiz.log_id.notes and 'Satuan' in wiz.log_id.notes)
    expect('imported account without password is inactive-safe',
           env['kopitera.account'].search([('login', '=', 'stafmigrasi.kopitera')]).user_id.has_group('kopitera_master.group_kitchen'))
    denied('migration log immutable', lambda: wiz.log_id.write({'notes': 'x'}))
    expect('template downloadable', wiz.action_download_template()['type'] == 'ir.actions.act_url')
    expect('imported recipe visible to staff bar', bool(env['kopitera.recipe'].with_user(staff).search([('menu_id', '=', matcha.id)])))

    print('KOPITERA_V120_CHECKS_PASSED=%s' % len(passed))
finally:
    env.cr.rollback()
