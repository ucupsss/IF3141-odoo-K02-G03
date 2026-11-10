"""Pengelolaan akun dan hak akses oleh Manager Area (UC-09, FR-10)."""
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError

ROLES = [
    ('manager', 'Manager Area'),
    ('head_bar', 'Head Bar'),
    ('head_kitchen', 'Head Kitchen'),
    ('head_floor', 'Head Floor'),
    ('mod', 'Manager on Duty'),
    ('staf_bar', 'Staf Bar'),
    ('staf_kitchen', 'Staf Kitchen'),
    ('developer', 'Pengembang Eksternal'),
]
ROLE_GROUPS = {
    'manager': 'group_manager', 'head_bar': 'group_head_bar', 'head_kitchen': 'group_head_kitchen',
    'head_floor': 'group_head_floor', 'mod': 'group_view_all', 'staf_bar': 'group_bar',
    'staf_kitchen': 'group_kitchen', 'developer': 'group_developer',
}
JOB_TITLES = {
    'manager': 'Manager Area (JB-02)', 'head_bar': 'Head Bar (JB-07)', 'head_kitchen': 'Head Kitchen (JB-08)',
    'head_floor': 'Head Floor (JB-09)', 'mod': 'Manager on Duty (JB-04)', 'staf_bar': 'Staf Bar (JB-11)',
    'staf_kitchen': 'Staf Kitchen (JB-12)', 'developer': 'Pengembang Eksternal (EXT-01)',
}
ROLE_RIGHTS = {
    'manager': 'Menyetujui/menolak pengajuan, merilis perubahan, memulihkan versi, mengelola akun, membuat laporan.',
    'head_bar': 'Mengajukan dan memeriksa data menu, bahan, dan resep minuman; melihat riwayat; membuat laporan.',
    'head_kitchen': 'Mengajukan dan memeriksa data menu, bahan, dan resep makanan; melihat riwayat; membuat laporan.',
    'head_floor': 'Melihat menu dan resep berlaku seluruh divisi, menerima notifikasi rilis, membuat laporan.',
    'mod': 'Melihat menu dan resep berlaku seluruh divisi (baca saja).',
    'staf_bar': 'Melihat resep dan gramasi minuman yang berlaku (baca saja).',
    'staf_kitchen': 'Melihat resep dan gramasi makanan yang berlaku (baca saja).',
    'developer': 'Memigrasikan data awal dari Excel dan melihat log migrasi.',
}
# Urutan penting: peran dengan hak paling luas dicek lebih dulu.
ROLE_PRIORITY = ['developer', 'manager', 'head_bar', 'head_kitchen', 'head_floor', 'mod', 'staf_bar', 'staf_kitchen']
BRANCHES = [('karawitan', 'Karawitan'), ('dago', 'Dago'), ('burangrang', 'Burangrang'), ('jakarta', 'Jakarta')]


class KopiteraAccount(models.Model):
    _name = 'kopitera.account'
    _description = 'Akun Pengguna Kopitera'
    _inherit = ['mail.thread']
    _order = 'state, role, name'

    name = fields.Char('Nama', required=True, tracking=True)
    login = fields.Char('Login', required=True, tracking=True)
    role = fields.Selection(ROLES, 'Peran Sistem', required=True, tracking=True)
    job_title = fields.Char('Jabatan', tracking=True)
    branch = fields.Selection(BRANCHES, 'Cabang', tracking=True)
    state = fields.Selection([('active', 'Aktif'), ('inactive', 'Nonaktif')], 'Status Akun',
                             default='active', readonly=True, tracking=True)
    user_id = fields.Many2one('res.users', 'Pengguna Odoo', readonly=True, ondelete='restrict', copy=False)
    rights = fields.Text('Hak Akses Peran', compute='_compute_rights')
    new_password = fields.Char('Password Baru', compute='_compute_new_password', inverse='_inverse_new_password',
                               help='Diisi saat membuat akun atau mengatur ulang password. Tidak ditampilkan kembali.')

    _sql_constraints = [('login_unique', 'UNIQUE(login)', 'Login sudah dipakai akun lain.')]

    @api.depends('role')
    def _compute_rights(self):
        for record in self:
            record.rights = ROLE_RIGHTS.get(record.role, '')

    def _compute_new_password(self):
        for record in self:
            record.new_password = ''

    def _inverse_new_password(self):
        for record in self:
            if record.new_password:
                if len(record.new_password) < 8:
                    raise ValidationError(_('Password minimal 8 karakter.'))
                record._check_manageable()
                record.user_id.sudo().write({'password': record.new_password})
                record.message_post(body=_('Password akun diatur ulang oleh %s.') % self.env.user.name)

    @api.onchange('role')
    def _onchange_role(self):
        if self.role:
            self.job_title = JOB_TITLES[self.role]

    def _check_manager(self):
        if not self.env.su and not self.env.user.has_group('kopitera_master.group_manager'):
            raise AccessError(_('Hanya Manager Area yang dapat mengelola akun.'))

    def _check_manageable(self):
        for record in self:
            user = record.user_id.sudo()
            if user and (user.has_group('base.group_system') or user.has_group('base.group_erp_manager') or user._is_superuser()):
                raise AccessError(_('Akun administrator sistem tidak dikelola melalui menu ini.'))

    @api.model
    def _role_group_ids(self):
        return [self.env.ref('kopitera_master.' + xmlid).id for xmlid in ROLE_GROUPS.values()]

    def _user_groups_command(self, role):
        return [(6, 0, [self.env.ref('base.group_user').id, self.env.ref('kopitera_master.' + ROLE_GROUPS[role]).id])]

    @api.model_create_multi
    def create(self, vals_list):
        self._check_manager()
        sync = self.env.context.get('kopitera_sync') and self.env.su
        for vals in vals_list:
            vals.setdefault('job_title', JOB_TITLES.get(vals.get('role')))
            if sync:
                continue
            if vals.get('user_id'):
                raise AccessError(_('Akun baru dibuat beserta pengguna Odoo-nya; tidak dapat menautkan pengguna lain.'))
            if not self.env.context.get('kopitera_import') and len(vals.get('new_password') or '') < 8:
                raise ValidationError(_('Isi password awal minimal 8 karakter.'))
            vals['state'] = 'active'
            if self.env['res.users'].sudo().with_context(active_test=False).search_count([('login', '=ilike', vals['login'].strip())]):
                raise ValidationError(_('Login "%s" sudah dipakai.') % vals['login'])
            user =self.env['res.users'].sudo().with_context(no_reset_password=True, mail_create_nosubscribe=True).create({
                'name': vals['name'], 'login': vals['login'].strip(), 'tz': 'Asia/Jakarta',
                'notification_type': 'inbox', 'groups_id': self._user_groups_command(vals['role']),
            })
            vals['user_id'] = user.id
        return super().create(vals_list)

    def write(self, vals):
        self._check_manager()
        if {'user_id', 'state'}.intersection(vals) and not self.env.su:
            raise AccessError(_('Gunakan tombol Aktifkan/Nonaktifkan untuk mengubah status akun.'))
        if {'role', 'login', 'name'}.intersection(vals):
            self._check_manageable()
            if 'role' in vals and any(record.user_id == self.env.user for record in self):
                raise UserError(_('Anda tidak dapat mengubah peran akun Anda sendiri.'))
        result = super().write(vals)
        for record in self:
            user_vals = {}
            if 'role' in vals:
                user_vals['groups_id'] = self._user_groups_command(record.role)
            if 'login' in vals:
                user_vals['login'] = record.login.strip()
            if 'name' in vals:
                user_vals['name'] = record.name
            if user_vals and record.user_id:
                record.user_id.sudo().write(user_vals)
        return result

    def unlink(self):
        raise UserError(_('Akun tidak dihapus agar riwayat aktivitas tetap utuh. Gunakan Nonaktifkan.'))

    def action_deactivate(self):
        self._check_manager()
        self._check_manageable()
        for record in self:
            if record.user_id == self.env.user:
                raise UserError(_('Anda tidak dapat menonaktifkan akun Anda sendiri.'))
            record.user_id.sudo().write({'active': False})
            record.sudo().write({'state': 'inactive'})
        return True

    def action_activate(self):
        self._check_manager()
        self._check_manageable()
        for record in self:
            record.user_id.sudo().write({'active': True})
            record.sudo().write({'state': 'active'})
        return True

    @api.model
    def _infer_role(self, user):
        for role in ROLE_PRIORITY:
            if user.has_group('kopitera_master.' + ROLE_GROUPS[role]):
                return role
        return False

    @api.model
    def action_sync_users(self):
        """Tautkan pengguna Odoo yang sudah memiliki peran Kopitera tetapi belum punya data akun."""
        self._check_manager()
        Users = self.env['res.users'].sudo().with_context(active_test=False)
        linked = self.sudo().search([]).mapped('user_id')
        created = self.browse()
        for user in Users.search([('share', '=', False), ('groups_id', 'in', self._role_group_ids())]) - linked:
            if user._is_superuser() or user.has_group('base.group_system') or user.has_group('base.group_erp_manager'):
                continue
            role = self._infer_role(user)
            if role:
                created |= self.sudo().with_context(kopitera_sync=True).create({
                    'name': user.name, 'login': user.login, 'role': role, 'user_id': user.id,
                    'state': 'active' if user.active else 'inactive',
                })
        return len(created)
