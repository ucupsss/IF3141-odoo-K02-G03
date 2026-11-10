"""Migrasi data awal dari Excel oleh Pengembang Eksternal (UC-13)."""
import base64
import io
import re
import zipfile

from lxml import etree
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

from .account import ROLES, BRANCHES

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL_NS = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'

SHEETS = {
    'Menu': ['Nama Menu', 'Divisi', 'Deskripsi', 'Alergen', 'Langkah Penyiapan'],
    'Bahan': ['Nama Bahan', 'Satuan', 'Area Penggunaan'],
    'Resep': ['Nama Menu', 'Nama Bahan', 'Takaran'],
    'Akun': ['Nama', 'Login', 'Peran', 'Cabang'],
}
DIVISION_ALIASES = {'bar': 'bar', 'minuman': 'bar', 'kitchen': 'kitchen', 'makanan': 'kitchen'}
AREA_ALIASES = dict(DIVISION_ALIASES, shared='shared', bersama='shared', **{'bar dan kitchen': 'shared'})
UNIT_ALIASES = {'g': 'g', 'gram': 'g', 'ml': 'ml', 'mililiter': 'ml', 'pcs': 'pcs', 'buah': 'pcs'}
ROLE_ALIASES = {label.lower(): key for key, label in ROLES} | {key: key for key, _label in ROLES}
BRANCH_ALIASES = {label.lower(): key for key, label in BRANCHES} | {key: key for key, _label in BRANCHES}


def read_xlsx(data):
    """Pembaca .xlsx minimal (tanpa openpyxl, karena tidak tersedia pada image odoo:17)."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise UserError(_('Berkas bukan file Excel .xlsx yang valid.')) from exc
    shared = []
    if 'xl/sharedStrings.xml' in archive.namelist():
        root = etree.fromstring(archive.read('xl/sharedStrings.xml'))
        shared = [''.join(si.itertext()) for si in root.findall('m:si', NS)]
    workbook = etree.fromstring(archive.read('xl/workbook.xml'))
    rels = etree.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
    targets = {rel.get('Id'): rel.get('Target') for rel in rels}
    sheets = {}
    for sheet in workbook.find('m:sheets', NS):
        target = targets[sheet.get(REL_NS)].lstrip('/')
        path = target if target.startswith('xl/') else 'xl/' + target
        root = etree.fromstring(archive.read(path))
        rows = []
        for row in root.iter('{%s}row' % NS['m']):
            values = {}
            for cell in row.findall('m:c', NS):
                col = re.match(r'[A-Z]+', cell.get('r', 'A')).group()
                index = 0
                for char in col:
                    index = index * 26 + ord(char) - 64
                kind, value = cell.get('t'), cell.find('m:v', NS)
                if kind == 'inlineStr':
                    text = ''.join(cell.find('m:is', NS).itertext())
                elif value is None:
                    text = ''
                elif kind == 's':
                    text = shared[int(value.text)]
                else:
                    text = value.text
                values[index - 1] = text
            if values:
                rows.append((int(row.get('r')), [values.get(i, '') for i in range(max(values) + 1)]))
        sheets[sheet.get('name').strip()] = rows
    return sheets


class KopiteraMigrationLog(models.Model):
    _name = 'kopitera.migration.log'
    _description = 'Log Migrasi Data Awal Kopitera'
    _order = 'id desc'

    name = fields.Char('Nomor Migrasi', readonly=True, default='Baru')
    file_name = fields.Char('Nama Berkas', readonly=True)
    import_time = fields.Datetime('Waktu Impor', readonly=True, default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', 'Pelaksana', readonly=True, default=lambda self: self.env.user)
    success_count = fields.Integer('Jumlah Berhasil', readonly=True)
    failed_count = fields.Integer('Jumlah Gagal', readonly=True)
    summary = fields.Text('Ringkasan per Data', readonly=True)
    notes = fields.Text('Catatan Hasil', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            raise AccessError(_('Log migrasi dibuat otomatis oleh sistem.'))
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('kopitera.migration.log') or 'Baru'
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.su:
            raise AccessError(_('Log migrasi tidak dapat diubah.'))
        return super().write(vals)

    def unlink(self):
        raise AccessError(_('Log migrasi tidak dapat dihapus.'))


class KopiteraImportWizard(models.TransientModel):
    _name = 'kopitera.import.wizard'
    _description = 'Migrasi Data Awal dari Excel'

    file_data = fields.Binary('Berkas Excel (.xlsx)')
    file_name = fields.Char('Nama Berkas')
    state = fields.Selection([('upload', 'Unggah'), ('preview', 'Pratinjau'), ('done', 'Selesai')], default='upload')
    preview_html = fields.Html('Pratinjau', readonly=True, sanitize=False)
    valid_count = fields.Integer('Baris Valid', readonly=True)
    invalid_count = fields.Integer('Baris Gagal', readonly=True)
    log_id = fields.Many2one('kopitera.migration.log', 'Log Migrasi', readonly=True)
    template_data = fields.Binary('Template', readonly=True, attachment=False)
    template_name = fields.Char(default='template-migrasi-kopitera.xlsx')

    def _check_developer(self):
        if not self.env.su and not (self.env.user.has_group('kopitera_master.group_developer')
                                    or self.env.user.has_group('base.group_system')):
            raise AccessError(_('Migrasi data hanya dijalankan Pengembang Eksternal.'))

    # ------------------------------------------------------------- template
    def action_download_template(self):
        self._check_developer()
        import xlsxwriter
        buffer = io.BytesIO()
        book = xlsxwriter.Workbook(buffer, {'in_memory': True})
        head = book.add_format({'bold': True, 'bg_color': '#E9ECEF', 'border': 1})
        notes = {
            'Menu': 'Divisi: bar atau kitchen',
            'Bahan': 'Satuan: g, ml, atau pcs | Area: bar, kitchen, atau shared',
            'Resep': 'Satu baris per bahan; takaran per porsi > 0',
            'Akun': 'Opsional. Peran: manager, head_bar, head_kitchen, head_floor, mod, staf_bar, staf_kitchen | Cabang: karawitan, dago, burangrang, jakarta',
        }
        for name, header in SHEETS.items():
            sheet = book.add_worksheet(name)
            for col, title in enumerate(header):
                sheet.write(0, col, title, head)
                sheet.set_column(col, col, 24)
            sheet.write(0, len(header) + 1, notes[name])
        book.close()
        self.write({'template_data': base64.b64encode(buffer.getvalue())})
        return {'type': 'ir.actions.act_url', 'target': 'self',
                'url': '/web/content/?model=%s&id=%s&field=template_data&filename_field=template_name&download=true' % (self._name, self.id)}

    # ------------------------------------------------------------ parsing
    def _parse(self):
        """Validasi seluruh baris tanpa menyimpan. Mengembalikan rencana impor dan daftar kesalahan."""
        self._check_developer()
        if not self.file_data:
            raise UserError(_('Pilih berkas Excel terlebih dahulu.'))
        if self.file_name and not self.file_name.lower().endswith('.xlsx'):
            raise UserError(_('Format berkas harus .xlsx.'))
        sheets = read_xlsx(base64.b64decode(self.file_data))
        missing = [name for name in ('Menu', 'Bahan', 'Resep') if name not in sheets]
        if missing:
            raise UserError(_('Lembar wajib tidak ditemukan: %s') % ', '.join(missing))

        def records(name):
            rows = sheets.get(name) or []
            if not rows:
                return []
            header = [str(h).strip().lower() for h in rows[0][1]]
            result = []
            for number, values in rows[1:]:
                item = {key: (str(values[header.index(key.lower())]).strip() if key.lower() in header and header.index(key.lower()) < len(values) else '')
                        for key in SHEETS[name]}
                if any(item.values()):
                    result.append((number, item))
            return result

        Menu = self.env['kopitera.menu'].sudo().with_context(active_test=False)
        Ingredient = self.env['kopitera.ingredient'].sudo().with_context(active_test=False)
        errors, plan = [], {'menus': [], 'ingredients': [], 'recipes': [], 'accounts': []}
        menu_names, ingredient_units = {}, {}

        for number, row in records('Menu'):
            key, division = row['Nama Menu'].lower(), DIVISION_ALIASES.get(row['Divisi'].lower())
            if not row['Nama Menu']:
                errors.append(('Menu', number, _('Nama menu kosong.')))
            elif not division:
                errors.append(('Menu', number, _('Divisi "%s" tidak dikenal (bar/kitchen).') % row['Divisi']))
            elif key in menu_names or Menu.search_count([('name', '=ilike', row['Nama Menu'])]):
                errors.append(('Menu', number, _('Menu "%s" sudah terdaftar.') % row['Nama Menu']))
            else:
                menu_names[key] = division
                plan['menus'].append((number, row, division))

        for number, row in records('Bahan'):
            key = row['Nama Bahan'].lower()
            unit, area = UNIT_ALIASES.get(row['Satuan'].lower()), AREA_ALIASES.get(row['Area Penggunaan'].lower())
            if not row['Nama Bahan']:
                errors.append(('Bahan', number, _('Nama bahan kosong.')))
            elif not unit:
                errors.append(('Bahan', number, _('Satuan "%s" bukan satuan baku (g/ml/pcs).') % row['Satuan']))
            elif not area:
                errors.append(('Bahan', number, _('Area "%s" tidak dikenal (bar/kitchen/shared).') % row['Area Penggunaan']))
            elif key in ingredient_units or Ingredient.search_count([('name', '=ilike', row['Nama Bahan'])]):
                errors.append(('Bahan', number, _('Bahan "%s" sudah terdaftar.') % row['Nama Bahan']))
            else:
                ingredient_units[key] = area
                plan['ingredients'].append((number, row, unit, area))

        grouped = {}
        for number, row in records('Resep'):
            grouped.setdefault(row['Nama Menu'].lower(), []).append((number, row))
        for key, lines in grouped.items():
            problems, seen = [], set()
            menu_division = menu_names.get(key)
            existing_menu = Menu.search([('name', '=ilike', lines[0][1]['Nama Menu'])], limit=1) if not menu_division else Menu
            if not menu_division and existing_menu:
                if existing_menu.current_recipe_id:
                    problems.append(_('Menu "%s" sudah memiliki resep berlaku.') % existing_menu.name)
                menu_division = existing_menu.division
            if not menu_division:
                problems.append(_('Menu "%s" tidak ada di lembar Menu maupun sistem.') % lines[0][1]['Nama Menu'])
            for number, row in lines:
                ing_key = row['Nama Bahan'].lower()
                area = ingredient_units.get(ing_key)
                if not area:
                    existing = Ingredient.search([('name', '=ilike', row['Nama Bahan']), ('active', '=', True)], limit=1)
                    area = existing.division if existing else None
                try:
                    quantity = float(str(row['Takaran']).replace(',', '.'))
                except ValueError:
                    quantity = 0
                if not area:
                    problems.append(_('baris %s: bahan "%s" tidak ditemukan') % (number, row['Nama Bahan']))
                elif menu_division and area not in ('shared', menu_division):
                    problems.append(_('baris %s: bahan "%s" tidak sesuai divisi menu') % (number, row['Nama Bahan']))
                if quantity <= 0:
                    problems.append(_('baris %s: takaran harus lebih dari nol') % number)
                if ing_key in seen:
                    problems.append(_('baris %s: bahan "%s" tercantum ganda') % (number, row['Nama Bahan']))
                seen.add(ing_key)
            if problems:
                errors.append(('Resep', ', '.join(str(n) for n, _row in lines), '; '.join(problems)))
            else:
                plan['recipes'].append((lines, key))

        Account = self.env['kopitera.account'].sudo()
        Users = self.env['res.users'].sudo().with_context(active_test=False)
        logins = set()
        for number, row in records('Akun'):
            role, branch = ROLE_ALIASES.get(row['Peran'].lower()), BRANCH_ALIASES.get(row['Cabang'].lower())
            login = row['Login'].strip()
            if not row['Nama'] or not login:
                errors.append(('Akun', number, _('Nama dan login wajib diisi.')))
            elif not role or role == 'developer':
                errors.append(('Akun', number, _('Peran "%s" tidak dikenal.') % row['Peran']))
            elif row['Cabang'] and not branch:
                errors.append(('Akun', number, _('Cabang "%s" tidak dikenal.') % row['Cabang']))
            elif login.lower() in logins or Users.search_count([('login', '=ilike', login)]) or Account.search_count([('login', '=ilike', login)]):
                errors.append(('Akun', number, _('Login "%s" sudah dipakai.') % login))
            else:
                logins.add(login.lower())
                plan['accounts'].append((number, row, role, branch))
        return plan, errors

    @staticmethod
    def _plan_size(plan):
        return (len(plan['menus']) + len(plan['ingredients']) + len(plan['accounts'])
                + sum(len(lines) for lines, _key in plan['recipes']))

    @staticmethod
    def _error_size(errors):
        return sum(len(str(where).split(',')) if sheet == 'Resep' else 1 for sheet, where, _msg in errors)

    def _render(self, plan, errors):
        counts = [('Menu', len(plan['menus'])), ('Bahan', len(plan['ingredients'])),
                  ('Resep (menu)', len(plan['recipes'])), ('Akun', len(plan['accounts']))]
        summary = Markup('').join(Markup('<tr><td>%s</td><td class="text-end">%s</td></tr>') % c for c in counts)
        html = (Markup('<h5>Data yang siap diimpor</h5><table class="table table-sm table-bordered w-auto">'
                       '<thead class="table-light"><tr><th>Lembar</th><th>Jumlah</th></tr></thead><tbody>%s</tbody></table>') % summary)
        if errors:
            rows = Markup('').join(Markup('<tr class="table-danger"><td>%s</td><td>%s</td><td>%s</td></tr>') % e for e in errors)
            html += (Markup('<h5>Baris yang akan gagal</h5><table class="table table-sm table-bordered">'
                            '<thead class="table-light"><tr><th>Lembar</th><th>Baris</th><th>Keterangan</th></tr></thead><tbody>%s</tbody></table>') % rows)
        else:
            html += Markup('<div class="alert alert-success">Semua baris valid.</div>')
        return html

    def action_preview(self):
        self.ensure_one()
        plan, errors = self._parse()
        self.write({'state': 'preview', 'preview_html': self._render(plan, errors),
                    'valid_count': self._plan_size(plan), 'invalid_count': self._error_size(errors)})
        return self._reopen()

    def action_back(self):
        self.write({'state': 'upload', 'preview_html': False})
        return self._reopen()

    def _reopen(self):
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id,
                'view_mode': 'form', 'target': 'new', 'name': _('Migrasi Data Awal dari Excel')}

    def action_import(self):
        self.ensure_one()
        plan, errors = self._parse()
        env = self.env(su=True)
        Menu, Ingredient, Recipe = env['kopitera.menu'], env['kopitera.ingredient'], env['kopitera.recipe']
        created = {'Menu': 0, 'Bahan': 0, 'Resep': 0, 'Akun': 0}
        instructions = {}
        for _number, row, division in plan['menus']:
            Menu.create({'name': row['Nama Menu'], 'division': division,
                         'description': row['Deskripsi'] or False, 'allergens': row['Alergen'] or False})
            instructions[row['Nama Menu'].lower()] = row['Langkah Penyiapan']
            created['Menu'] += 1
        for _number, row, unit, area in plan['ingredients']:
            Ingredient.create({'name': row['Nama Bahan'], 'unit': unit, 'division': area})
            created['Bahan'] += 1
        Menu, Ingredient = Menu.with_context(active_test=True), Ingredient.with_context(active_test=True)
        for lines, key in plan['recipes']:
            menu = Menu.search([('name', '=ilike', lines[0][1]['Nama Menu'])], limit=1)
            recipe = Recipe.with_user(self.env.user).sudo().create({
                'menu_id': menu.id,
                'reason': _('Versi awal hasil migrasi data dari %s.') % (self.file_name or 'Excel'),
                'instructions': instructions.get(key) or _('Mengikuti resep hasil migrasi data awal.'),
                'line_ids': [(0, 0, {'ingredient_id': Ingredient.search([('name', '=ilike', row['Nama Bahan'])], limit=1).id,
                                     'quantity': float(str(row['Takaran']).replace(',', '.'))}) for _n, row in lines],
            })
            recipe._transition({'state': 'published', 'version': 1, 'released_at': fields.Datetime.now(),
                                'author_id': self.env.uid})
            menu.write({'current_recipe_id': recipe.id})
            recipe.message_post(body=_('Versi 1 dibuat dari migrasi data awal oleh %s.') % self.env.user.name)
            recipe._kp_log('import', before=_('Belum ada resep di sistem.'), note=_('Berkas: %s') % (self.file_name or '-'))
            recipe._kp_sync_bom()
            created['Resep'] += len(lines)
        Account = env['kopitera.account'].with_context(kopitera_import=True)
        for _number, row, role, branch in plan['accounts']:
            Account.create({'name': row['Nama'], 'login': row['Login'], 'role': role, 'branch': branch or False})
            created['Akun'] += 1
        success, failed = sum(created.values()), self._error_size(errors)
        notes = '\n'.join('[%s baris %s] %s' % e for e in errors) or _('Tidak ada baris gagal.')
        if plan['accounts']:
            notes += '\n' + _('Akun hasil migrasi belum memiliki password; Manager Area mengaturnya melalui menu Akun Pengguna.')
        log = env['kopitera.migration.log'].create({
            'file_name': self.file_name, 'user_id': self.env.uid, 'success_count': success, 'failed_count': failed,
            'summary': '\n'.join('%s: %s baris berhasil' % item for item in created.items()), 'notes': notes,
        })
        self.write({'state': 'done', 'log_id': log.id, 'valid_count': success, 'invalid_count': failed,
                    'preview_html': self._render(plan, errors)})
        return self._reopen()
