"""Penyelarasan data setelah pemasangan atau upgrade (17.0.1.2.0 dan 17.0.1.3.0)."""


def sync_existing_data(env):
    # Docker: Odoo di dalam container mendengarkan port 8069, sedangkan browser memakai port lain (mis. 8070).
    # wkhtmltopdf mengambil CSS laporan dari report.url; tanpa ini PDF laporan tampil tanpa gaya.
    params = env['ir.config_parameter'].sudo()
    if not params.get_param('report.url'):
        params.set_param('report.url', 'http://localhost:8069')
    # Head Floor kini memiliki grup sendiri (laporan + notifikasi rilis). Akun uji lama dipindahkan.
    view_all = env.ref('kopitera_master.group_view_all')
    head_floor = env.ref('kopitera_master.group_head_floor')
    for user in view_all.users.filtered(lambda u: u.login.startswith('headfloor')):
        user.write({'groups_id': [(4, head_floor.id)]})
    # Pengembang Eksternal: admin tetap dapat menjalankan migrasi.
    env.ref('base.user_admin').write({'groups_id': [(4, env.ref('kopitera_master.group_developer').id)]})
    # Tautkan pengguna Kopitera yang sudah ada ke data Akun (UC-09).
    env['kopitera.account'].sudo().action_sync_users()
    # Resep yang sudah berlaku disalin menjadi BoM Manufacturing.
    recipes = env['kopitera.recipe'].sudo().search([('state', '=', 'published'), ('bom_id', '=', False)])
    recipes._kp_sync_bom()
    # Lengkapi versi sebelumnya untuk resep yang dirilis sebelum field ini ada.
    Recipe = env['kopitera.recipe'].sudo()
    for menu in env['kopitera.menu'].sudo().with_context(active_test=False).search([]):
        versions = Recipe.search([('menu_id', '=', menu.id), ('state', 'in', ['published', 'archived']),
                                  ('version', '>', 0)], order='version')
        for older, newer in zip(versions, versions[1:]):
            if not newer.previous_recipe_id:
                newer.write({'previous_recipe_id': older.id})


def fill_menu_categories(env):
    """Menu lama belum memiliki kategori: isi tebakan awal dari jenis menu (dapat diubah lewat pengajuan)."""
    Menu = env['kopitera.menu'].sudo().with_context(active_test=False)
    for menu in Menu.search([('category', '=', False)]):
        name = menu.name.lower()
        if menu.division == 'bar':
            category = 'coffee' if any(word in name for word in ('kopi', 'coffee', 'espresso', 'latte')) else 'non_coffee'
        else:
            category = ('rice_bowl' if 'rice bowl' in name else 'pasta' if any(w in name for w in ('pasta', 'spaghetti'))
                        else 'dessert' if any(w in name for w in ('cake', 'dessert', 'pudding')) else 'main_course')
        # SQL langsung agar nomor revisi data menu tidak bertambah karena penyelarasan teknis.
        env.cr.execute('UPDATE kopitera_menu SET category = %s WHERE id = %s', [category, menu.id])
    env.cr.execute("UPDATE kopitera_menu SET availability = 'available' WHERE availability IS NULL")
    Menu.invalidate_model(['category', 'availability'])


def post_init_hook(env):
    sync_existing_data(env)
    fill_menu_categories(env)
