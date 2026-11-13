"""Run through Odoo shell. Add two draft fixtures, never modify existing demo proposals."""
author = env['res.users'].search([('login', '=', 'headbar.kopitera')], limit=1)
if not author:
    raise RuntimeError('Create local demonstration accounts first.')
samples = [
    ('demo_change_menu_lemon', {
        'kind': 'menu', 'operation': 'create', 'division': 'bar',
        'proposed_name': 'Es Teh Lemon — Contoh', 'category': 'non_coffee', 'availability': 'available',
        'description': 'Minuman contoh untuk latihan pengajuan menu. Bukan menu operasional Kopitera.',
        'allergens': 'Tidak ditetapkan; perlu pemeriksaan',
        'reason': 'Latihan penambahan menu baru untuk Milestone 4; data fiktif.',
    }),
    ('demo_change_ingredient_vanilla', {
        'kind': 'ingredient', 'operation': 'create', 'division': 'bar',
        'proposed_name': 'Sirup Vanila — Contoh', 'unit': 'ml', 'usage': 'bar',
        'reason': 'Latihan penambahan bahan baku untuk Milestone 4; data fiktif.',
    }),
]
created = 0
for xmlid, values in samples:
    if not env.ref('kopitera_master.' + xmlid, raise_if_not_found=False):
        record = env['kopitera.master.change'].with_user(author).create(values)
        env['ir.model.data'].create({'module': 'kopitera_master', 'name': xmlid,
                                    'model': record._name, 'res_id': record.id, 'noupdate': True})
        created += 1
env.cr.commit()
print('MASTER_DEMO_DRAFTS_CREATED=' + str(created))
