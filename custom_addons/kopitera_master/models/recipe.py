from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


# Pengajuan yang sudah dikirim dan belum selesai. Draf yang belum dikirim tidak menghalangi pengaju lain;
# yang lebih dulu dikirim diproses, draf lain ditolak saat dikirim (FR-05).
OPEN_STATES = ['review', 'revision', 'approval', 'approved']
DIVISIONS = [('bar', 'Minuman / Bar'), ('kitchen', 'Makanan / Kitchen')]
MENU_CATEGORIES = [
    ('coffee', 'Kopi'), ('non_coffee', 'Non-Kopi'),
    ('light_meal', 'Light Meals'), ('main_course', 'Main Course'), ('rice_bowl', 'Rice Bowl'),
    ('pasta', 'Pasta'), ('dessert', 'Dessert'),
]
CATEGORY_DIVISION = {'coffee': 'bar', 'non_coffee': 'bar', 'light_meal': 'kitchen', 'main_course': 'kitchen',
                     'rice_bowl': 'kitchen', 'pasta': 'kitchen', 'dessert': 'kitchen'}
AVAILABILITY = [('available', 'Tersedia'), ('seasonal', 'Musiman / Terbatas'), ('unavailable', 'Tidak Tersedia')]
# Satuan baku bahan (FR-02). Satuan takaran resep boleh berbeda asalkan satu kategori (FR-04).
UNITS = [('g', 'gram'), ('kg', 'kilogram'), ('ml', 'mililiter'), ('l', 'liter'), ('pcs', 'buah')]
UNIT_CATEGORY = {'g': 'mass', 'kg': 'mass', 'ml': 'volume', 'l': 'volume', 'pcs': 'unit'}
UNIT_FACTOR = {'g': 1, 'kg': 1000, 'ml': 1, 'l': 1000, 'pcs': 1}


def to_base(quantity, unit, base_unit):
    """Konversi takaran ke satuan baku bahan (mis. 0,2 kg -> 200 g)."""
    if not unit or not base_unit:
        return quantity or 0.0
    return (quantity or 0.0) * UNIT_FACTOR[unit] / UNIT_FACTOR[base_unit]


def precise_enough(quantity, unit, division):
    """QR-6: ketelitian 0,1 g/ml untuk Bar dan 1 g/ml untuk Kitchen (0,2 kg = 200 g lolos untuk dapur)."""
    step = 1.0 if division == 'kitchen' else 0.1
    amount = (quantity or 0.0) * UNIT_FACTOR[unit] / step
    return abs(amount - round(amount)) <= 1e-6


class KopiteraMenu(models.Model):
    _name = 'kopitera.menu'
    _description = 'Menu Kopitera'
    _order = 'name'

    name = fields.Char('Nama Menu', required=True)
    division = fields.Selection(DIVISIONS, 'Jenis Menu', required=True)
    category = fields.Selection(MENU_CATEGORIES, 'Kategori')
    description = fields.Text('Deskripsi')
    allergens = fields.Char('Alergen')
    availability = fields.Selection(AVAILABILITY, 'Status Ketersediaan', default='available')
    current_recipe_id = fields.Many2one('kopitera.recipe', 'Resep Berlaku', readonly=True, copy=False)

    def action_propose_recipe(self):
        self.ensure_one()
        self.check_access_rights('read')
        self.check_access_rule('read')
        if not self.env.user.has_group('kopitera_master.group_editor'):
            raise AccessError(_('Hanya pengaju yang dapat membuat draf resep.'))
        open_recipe = self.env['kopitera.recipe'].sudo().search(
            [('menu_id', '=', self.id), ('state', 'in', OPEN_STATES)], limit=1)
        if open_recipe:
            raise UserError(_('Menu ini masih memiliki pengajuan resep %s (%s) yang belum selesai. Lanjutkan pengajuan '
                              'tersebut atau tunggu sampai dirilis/ditolak.') % (
                open_recipe.name, dict(open_recipe._fields['state'].selection)[open_recipe.state]))
        current = self.current_recipe_id
        proposal = self.env['kopitera.recipe'].create({
            'menu_id': self.id,
            'portion_qty': current.portion_qty or 1,
            'instructions': current.instructions or '',
            'line_ids': [(0, 0, {'ingredient_id': line.ingredient_id.id, 'quantity': line.quantity, 'unit': line.unit})
                         for line in current.line_ids],
        })
        return {'type': 'ir.actions.act_window', 'name': _('Draf Resep'),
                'res_model': 'kopitera.recipe', 'res_id': proposal.id, 'view_mode': 'form'}


class KopiteraIngredient(models.Model):
    _name = 'kopitera.ingredient'
    _description = 'Bahan Baku Kopitera'
    _order = 'name'

    name = fields.Char('Nama Bahan', required=True)
    unit = fields.Selection(UNITS, 'Satuan Baku', required=True)
    division = fields.Selection(DIVISIONS + [('shared', 'Bar dan Kitchen')], 'Area Penggunaan', required=True)


class KopiteraRecipe(models.Model):
    _name = 'kopitera.recipe'
    _description = 'Pengajuan dan Versi Resep Kopitera'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char('Nomor Pengajuan', readonly=True, default='Baru', copy=False)
    menu_id = fields.Many2one('kopitera.menu', 'Menu', required=True, ondelete='restrict', tracking=True)
    division = fields.Selection(related='menu_id.division', store=True, string='Divisi')
    portion_qty = fields.Integer('Jumlah Porsi', default=1, tracking=True,
                                 help='Jumlah porsi standar yang dihasilkan satu kali penyiapan. Takaran ditulis per porsi.')
    proposed_release_date = fields.Date('Usulan Tanggal Rilis', tracking=True,
                                        help='Usulan pengaju; tanggal rilis final ditetapkan Manager Area.')
    author_id = fields.Many2one('res.users', 'Pengaju', default=lambda self: self.env.user, readonly=True)
    state = fields.Selection([
        ('draft', 'Draf'), ('review', 'Menunggu Pemeriksaan'),
        ('revision', 'Perlu Perbaikan'), ('approval', 'Menunggu Persetujuan'),
        ('approved', 'Menunggu Rilis'), ('rejected', 'Ditolak'),
        ('published', 'Berlaku'), ('archived', 'Arsip'),
    ], 'Status', default='draft', required=True, readonly=True, tracking=True, copy=False)
    reason = fields.Text('Alasan Pengajuan', tracking=True)
    instructions = fields.Text('Langkah Penyiapan', tracking=True)
    line_ids = fields.One2many('kopitera.recipe.line', 'recipe_id', 'Komposisi dan Gramasi', copy=True)
    review_note = fields.Text('Catatan Pemeriksaan', tracking=True, copy=False)
    reviewer_id = fields.Many2one('res.users', 'Diperiksa oleh', readonly=True, copy=False)
    decision_note = fields.Text('Alasan Keputusan', tracking=True, copy=False)
    approver_id = fields.Many2one('res.users', 'Disetujui / Ditolak oleh', readonly=True, copy=False)
    release_date = fields.Date('Tanggal Rilis', tracking=True, copy=False)
    released_at = fields.Datetime('Waktu Rilis', readonly=True, copy=False)
    version = fields.Integer('Versi', readonly=True, copy=False)
    is_author = fields.Boolean(compute='_compute_is_author')

    @api.depends_context('uid')
    @api.depends('author_id')
    def _compute_is_author(self):
        for record in self:
            record.is_author = record.author_id == self.env.user

    @api.model_create_multi
    def create(self, vals_list):
        protected = {'state', 'version', 'reviewer_id', 'approver_id', 'released_at',
                     'review_note', 'decision_note', 'release_date', 'name', 'author_id', 'division'}
        for vals in vals_list:
            if protected.intersection(vals) and not self.env.su:
                raise AccessError(_('Status dan keputusan hanya dapat diubah melalui alur persetujuan.'))
            vals['author_id'] = self.env.uid
            vals['name'] = self.env['ir.sequence'].next_by_code('kopitera.recipe') or 'Baru'
            # Explicit defaults also prevent RPC context default_* from skipping the workflow.
            vals.update(state='draft', version=0, reviewer_id=False, approver_id=False,
                        released_at=False, review_note=False, decision_note=False, release_date=False)
        return super().create(vals_list)

    def _check_content_edit(self):
        self.check_access_rights('write')
        self.check_access_rule('write')
        for record in self:
            if record.state not in ('draft', 'revision'):
                raise UserError(_('Isi resep hanya dapat diubah saat Draf atau Perlu Perbaikan.'))
            if record.author_id != self.env.user and not self.env.su:
                raise AccessError(_('Hanya pengaju yang dapat mengubah isi draf ini.'))

    def write(self, vals):
        protected = {'state', 'version', 'reviewer_id', 'approver_id', 'released_at', 'name', 'author_id', 'division'}
        if protected.intersection(vals) and not self.env.su:
            raise AccessError(_('Gunakan tombol alur pengajuan untuk mengubah status.'))
        if {'menu_id', 'reason', 'instructions', 'line_ids', 'portion_qty', 'proposed_release_date'}.intersection(vals):
            self._check_content_edit()
        if 'review_note' in vals:
            self._check_step('review', 'group_editor')
            if any(record.author_id == self.env.user for record in self) and not self.env.su:
                raise UserError(_('Pengaju tidak dapat memeriksa pengajuannya sendiri.'))
        if {'decision_note', 'release_date'}.intersection(vals):
            self._check_step('approval', 'group_manager')
        result = super().write(vals)
        if 'menu_id' in vals:
            self.line_ids._check_division()
        return result

    def unlink(self):
        self._check_content_edit()
        return super().unlink()

    def _check_step(self, state, group):
        self.check_access_rights('write')
        self.check_access_rule('write')
        if not self.env.su and not self.env.user.has_group('kopitera_master.' + group):
            raise AccessError(_('Peran Anda tidak diizinkan menjalankan tindakan ini.'))
        if any(record.state != state for record in self):
            raise UserError(_('Status pengajuan tidak sesuai untuk tindakan ini.'))

    def _transition(self, vals):
        # A private helper cannot be called through RPC. Keep the acting user for audit tracking.
        return super(KopiteraRecipe, self).write(vals)

    def _notify_group(self, group_xmlid, summary):
        group = self.env.ref('kopitera_master.' + group_xmlid)
        for record in self:
            for user in group.sudo().users.filtered(lambda u: u.active and u.id != self.env.uid):
                if record.with_user(user).search_count([('id', '=', record.id)]):
                    record.activity_schedule('mail.mail_activity_data_todo', user_id=user.id, summary=summary)

    def _finish_activities(self):
        self.activity_ids.action_feedback(feedback=_('Tahap pengajuan sudah diproses.'))

    def action_submit(self):
        self._check_content_edit()
        for record in self:
            if not record.line_ids or not (record.reason or '').strip() or not (record.instructions or '').strip():
                raise ValidationError(_('Isi komposisi, alasan pengajuan, dan langkah penyiapan terlebih dahulu.'))
            if record.portion_qty < 1:
                raise ValidationError(_('Jumlah porsi minimal 1.'))
            other = self.sudo().search([('menu_id', '=', record.menu_id.id), ('id', '!=', record.id),
                                        ('state', 'in', OPEN_STATES)], limit=1)
            if other:
                raise UserError(_('Pengajuan ditolak: menu %s masih memiliki pengajuan resep %s yang belum selesai.')
                                % (record.menu_id.name, other.name))
        self._transition({'state': 'review'})
        self._finish_activities()
        self._notify_group('group_editor', _('Periksa pengajuan resep Kopitera'))
        return True

    def action_review(self):
        self._check_step('review', 'group_editor')
        if any(record.author_id == self.env.user for record in self):
            raise UserError(_('Pengaju tidak dapat memeriksa pengajuannya sendiri.'))
        if any(not (record.review_note or '').strip() for record in self):
            raise ValidationError(_('Isi catatan pemeriksaan terlebih dahulu.'))
        self._transition({'state': 'approval', 'reviewer_id': self.env.uid})
        self._finish_activities()
        self._notify_group('group_manager', _('Putuskan pengajuan resep Kopitera'))
        return True

    def action_return(self):
        self._check_step('review', 'group_editor')
        if any(record.author_id == self.env.user or not (record.review_note or '').strip() for record in self):
            raise ValidationError(_('Pemeriksa harus berbeda dari pengaju dan catatan perbaikan wajib diisi.'))
        self._transition({'state': 'revision', 'reviewer_id': self.env.uid})
        self._finish_activities()
        for record in self:
            record.activity_schedule('mail.mail_activity_data_todo', user_id=record.author_id.id,
                                     summary=_('Perbaiki pengajuan resep Kopitera'))
        return True

    def action_approve(self):
        self._check_step('approval', 'group_manager')
        if any(not record.release_date or not (record.decision_note or '').strip() for record in self):
            raise ValidationError(_('Isi tanggal rilis dan alasan keputusan terlebih dahulu.'))
        self._transition({'state': 'approved', 'approver_id': self.env.uid})
        self._finish_activities()
        self._notify_group('group_manager', _('Rilis resep pada tanggal yang ditetapkan'))
        return True

    def action_reject(self):
        self._check_step('approval', 'group_manager')
        if any(not (record.decision_note or '').strip() for record in self):
            raise ValidationError(_('Alasan penolakan wajib diisi.'))
        self._transition({'state': 'rejected', 'approver_id': self.env.uid})
        self._finish_activities()
        return True

    def action_release(self):
        self._check_step('approved', 'group_manager')
        today = fields.Date.context_today(self)
        for record in self:
            if not record.release_date or record.release_date > today:
                raise UserError(_('Pengajuan baru dapat dirilis pada atau setelah tanggal rilis.'))
            self.env.cr.execute('SELECT id FROM kopitera_menu WHERE id = %s FOR UPDATE', [record.menu_id.id])
            record.menu_id.invalidate_recordset(['current_recipe_id'])
            previous = record.menu_id.current_recipe_id
            version = previous.version + 1 if previous else 1
            if previous:
                previous._transition({'state': 'archived'})
            record._transition({'state': 'published', 'version': version, 'released_at': fields.Datetime.now()})
            record.menu_id.sudo().write({'current_recipe_id': record.id})
            record.message_post(body=_('Resep versi %s dirilis dan berlaku di seluruh cabang.') % version)
        self._finish_activities()
        return True


class KopiteraRecipeLine(models.Model):
    _name = 'kopitera.recipe.line'
    _description = 'Komposisi dan Gramasi Resep'

    recipe_id = fields.Many2one('kopitera.recipe', required=True, ondelete='cascade')
    ingredient_id = fields.Many2one('kopitera.ingredient', 'Bahan Baku', required=True, ondelete='restrict')
    quantity = fields.Float('Takaran per Porsi', required=True, digits=(12, 1))
    unit = fields.Selection(UNITS, 'Satuan Takaran', compute='_compute_unit', store=True, readonly=False, precompute=True)
    base_unit = fields.Selection(related='ingredient_id.unit', string='Satuan Baku')

    _sql_constraints = [
        ('positive_quantity', 'CHECK(quantity > 0)', 'Takaran harus lebih besar dari nol.'),
        ('unique_ingredient', 'UNIQUE(recipe_id, ingredient_id)', 'Bahan yang sama cukup ditulis satu kali.'),
    ]

    @api.depends('ingredient_id')
    def _compute_unit(self):
        for line in self:
            base = line.ingredient_id.unit
            if base and (not line.unit or UNIT_CATEGORY[line.unit] != UNIT_CATEGORY[base]):
                line.unit = base

    def _base_quantity(self):
        self.ensure_one()
        return to_base(self.quantity, self.unit, self.ingredient_id.unit)

    @api.constrains('unit', 'ingredient_id', 'quantity')
    def _check_unit_precision(self):
        for line in self:
            base = line.ingredient_id.unit
            if line.unit and base and UNIT_CATEGORY[line.unit] != UNIT_CATEGORY[base]:
                raise ValidationError(_('Satuan takaran %s tidak satu kategori dengan satuan baku %s untuk bahan %s.') % (
                    dict(UNITS)[line.unit], dict(UNITS)[base], line.ingredient_id.name))
            # QR-6: Bar teliti 0,1 g/ml; Kitchen dicatat dalam bilangan bulat (1 g/ml). Dihitung dalam g/ml/buah.
            if line.unit and not precise_enough(line.quantity, line.unit, line.recipe_id.division):
                raise ValidationError(_('Takaran %s melebihi ketelitian %s.') % (
                    line.ingredient_id.name, _('dapur (1 g/ml)') if line.recipe_id.division == 'kitchen' else _('bar (0,1 g/ml)')))

    @api.constrains('ingredient_id', 'recipe_id')
    def _check_division(self):
        for line in self:
            if line.ingredient_id.division not in ('shared', line.recipe_id.division):
                raise ValidationError(_('Bahan harus sesuai dengan area penggunaan resep.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('recipe_id'):
                raise ValidationError(_('Komposisi harus dibuat dari formulir pengajuan resep.'))
            self.env['kopitera.recipe'].browse(vals.get('recipe_id'))._check_content_edit()
        return super().create(vals_list)

    def write(self, vals):
        self.mapped('recipe_id')._check_content_edit()
        if 'recipe_id' in vals:
            raise AccessError(_('Baris komposisi tidak dapat dipindahkan ke pengajuan lain.'))
        return super().write(vals)

    def unlink(self):
        self.mapped('recipe_id')._check_content_edit()
        return super().unlink()
