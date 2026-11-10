"""Penyelarasan data setelah pemasangan atau upgrade ke 17.0.1.2.0."""


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


def post_init_hook(env):
    sync_existing_data(env)
