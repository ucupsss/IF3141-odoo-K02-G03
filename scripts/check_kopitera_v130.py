"""Uji fitur 17.0.1.3.0 lewat Odoo shell. Semua perubahan dibatalkan (rollback) di akhir.

Cakupan: kategori dan status ketersediaan menu (FR-01), satuan kg/l dan nama unik (FR-02), daftar resep
pada penolakan penonaktifan bahan (FR-03), satuan takaran satu kategori dan ketelitian QR-6 (FR-04),
penolakan pengajuan ganda (FR-05), jumlah porsi dan usulan tanggal rilis, serta laporan CSV dan filter versi (FR-12).
"""
import base64

from odoo import fields
from odoo.exceptions import UserError, ValidationError

passed = []


def expect(label, condition):
    assert condition, label
    passed.append(label)
    print('PASS', label)


def denied(label, function):
    try:
        with env.cr.savepoint():
            function()
    except (UserError, ValidationError) as error:
        passed.append(label)
        print('PASS', label, '->', str(error.args[0])[:90])
        return
    raise AssertionError(label + ' (tidak ditolak)')


try:
    user = lambda key: env['res.users'].search([('login', '=', key + '.kopitera')], limit=1)
    hb, rb, hk, rk, mg = [user(k) for k in ('headbar', 'reviewerbar', 'headkitchen', 'reviewerkitchen', 'manager')]
    Change, Recipe = env['kopitera.master.change'], env['kopitera.recipe']
    kopi, nasi = env.ref('kopitera_master.menu_kopi_susu'), env.ref('kopitera_master.menu_nasi_goreng')
    milk = env.ref('kopitera_master.ingredient_milk')

    def flow(record, author, reviewer):
        record.with_user(author).action_submit()
        record.with_user(reviewer).write({'review_note': 'Sesuai'})
        record.with_user(reviewer).action_review()
        record.with_user(mg).write({'decision_note': 'Disetujui', 'release_date': fields.Date.today()})
        record.with_user(mg).action_approve()
        record.with_user(mg).action_release()

    expect('menu lama memiliki kategori dan status ketersediaan', all(m.category and m.availability for m in env['kopitera.menu'].search([])))
    expect('satuan takaran baris lama terisi', all(line.unit for line in Recipe.search([]).line_ids))

    # FR-01
    base = {'kind': 'menu', 'operation': 'create', 'division': 'bar', 'reason': 'Uji v1.3.0', 'allergens': '-'}
    denied('menu tanpa kategori ditolak', lambda: Change.with_user(hb).create(dict(base, proposed_name='Uji A')).action_submit())
    denied('kategori harus sesuai jenis menu', lambda: Change.with_user(hb).create(dict(base, proposed_name='Uji B', category='pasta')).action_submit())
    denied('nama menu terdaftar ditolak', lambda: Change.with_user(hb).create(dict(base, proposed_name=kopi.name.upper(), category='coffee')).action_submit())
    menu_change = Change.with_user(hb).create(dict(base, proposed_name='Matcha Uji v130', category='non_coffee',
                                                   availability='seasonal', proposed_release_date=fields.Date.today()))
    flow(menu_change, hb, rb)
    new_menu = menu_change.result_menu_id
    expect('menu baru dirilis dengan kategori dan ketersediaan', new_menu.category == 'non_coffee' and new_menu.availability == 'seasonal')

    # FR-02
    ing = {'kind': 'ingredient', 'operation': 'create', 'reason': 'Uji v1.3.0'}
    denied('nama bahan terdaftar ditolak', lambda: Change.with_user(hb).create(dict(ing, division='bar', usage='bar', unit='ml', proposed_name='espresso')).action_submit())
    flour = Change.with_user(hk).create(dict(ing, division='kitchen', usage='kitchen', unit='kg', proposed_name='Tepung Uji v130'))
    flow(flour, hk, rk)
    expect('bahan bersatuan kilogram dapat dirilis', flour.result_ingredient_id.unit == 'kg')

    # FR-03
    denied('penonaktifan bahan terpakai menyebut resepnya', lambda: Change.with_user(hb).create(
        {'kind': 'ingredient', 'operation': 'deactivate', 'division': 'bar', 'ingredient_id': milk.id, 'reason': 'x'}).action_submit())

    # FR-04 + QR-6
    draft = Recipe.browse(nasi.with_user(hk).action_propose_recipe()['res_id'])
    gram_line = draft.line_ids.filtered(lambda l: l.ingredient_id.unit == 'g')[:1]
    denied('satuan lintas kategori ditolak', lambda: gram_line.with_user(hk).write({'unit': 'ml'}))
    denied('takaran dapur harus bilangan bulat', lambda: gram_line.with_user(hk).write({'quantity': 180.5}))
    gram_line.with_user(hk).write({'quantity': 0.2, 'unit': 'kg'})
    draft.with_user(hk).write({'portion_qty': 2, 'proposed_release_date': fields.Date.today(), 'reason': 'Uji satuan kg'})
    expect('perbandingan memakai satuan baku', '>200<' in draft.comparison_html)
    # FR-05
    second = Recipe.browse(nasi.with_user(hk).action_propose_recipe()['res_id'])
    second.with_user(hk).write({'reason': 'Draf kedua'})
    draft.with_user(hk).action_submit()
    denied('draf lain ditolak saat dikirim', lambda: second.with_user(hk).action_submit())
    denied('pengajuan baru ditolak saat ada yang terbuka', lambda: nasi.with_user(hk).action_propose_recipe())
    draft.with_user(rk).write({'review_note': 'Sesuai'})
    draft.with_user(rk).action_review()
    draft.with_user(mg).write({'decision_note': 'Disetujui', 'release_date': fields.Date.today()})
    draft.with_user(mg).action_approve()
    draft.with_user(mg).action_release()
    bom_line = draft.sudo().bom_id.bom_line_ids.filtered(lambda l: l.product_qty == 0.2)
    expect('BoM memakai satuan takaran kg', bom_line and bom_line.product_uom_id == env.ref('uom.product_uom_kgm'))

    # FR-12
    Wizard = env['kopitera.report.wizard'].with_user(mg)
    csv_wizard = Wizard.create({'report_type': 'catalog', 'category': 'non_coffee', 'output_format': 'csv'})
    csv_wizard.action_export()
    content = base64.b64decode(csv_wizard.file_data).decode('utf-8-sig')
    expect('ekspor CSV memuat kategori sesuai filter', csv_wizard.file_name.endswith('.csv') and 'Matcha Uji v130' in content and kopi.name not in content)
    _header, rows = Wizard.create({'report_type': 'recipe', 'version_no': 1})._get_table()
    expect('filter nomor versi', rows and all(row[1] == 1 for row in rows))
    html = env['ir.actions.report'].sudo()._render_qweb_html('kopitera_master.report_kopitera_document',
                                                             Wizard.create({'report_type': 'recipe'}).ids)[0]
    expect('lembar resep PDF memuat jumlah porsi', b'Jumlah porsi' in html)
    print('KOPITERA_V130_CHECKS_PASSED=%s' % len(passed))
finally:
    env.cr.rollback()
