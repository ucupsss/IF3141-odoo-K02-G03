from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError

from .recipe import DIVISIONS


class MasterChange(models.Model):
    _name = 'kopitera.master.change'
    _description = 'Pengajuan Menu dan Bahan Baku'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char('Nomor Pengajuan', default='Baru', readonly=True, copy=False)
    kind = fields.Selection([('menu', 'Menu'), ('ingredient', 'Bahan Baku')], 'Jenis Data', required=True, default='menu')
    operation = fields.Selection([('create', 'Tambah Baru'), ('update', 'Ubah Data'), ('deactivate', 'Nonaktifkan')], 'Tindakan', required=True, default='create')
    division = fields.Selection(DIVISIONS, 'Divisi Pengaju', required=True,
                                default=lambda self: 'kitchen' if self.env.user.has_group('kopitera_master.group_head_kitchen') else 'bar')
    menu_id = fields.Many2one('kopitera.menu', 'Menu Tujuan', ondelete='restrict')
    ingredient_id = fields.Many2one('kopitera.ingredient', 'Bahan Tujuan', ondelete='restrict')
    proposed_name = fields.Char('Nama yang Diusulkan')
    description = fields.Text('Deskripsi yang Diusulkan')
    allergens = fields.Char('Alergen yang Diusulkan')
    unit = fields.Selection([('g', 'gram'), ('ml', 'mililiter'), ('pcs', 'buah')], 'Satuan Baku')
    usage = fields.Selection(DIVISIONS + [('shared', 'Bar dan Kitchen')], 'Area Penggunaan',
                             default=lambda self: 'kitchen' if self.env.user.has_group('kopitera_master.group_head_kitchen') else 'bar')
    reason = fields.Text('Alasan Pengajuan', tracking=True)
    author_id = fields.Many2one('res.users', 'Pengaju', default=lambda self: self.env.user, readonly=True)
    reviewer_id = fields.Many2one('res.users', 'Diperiksa oleh', readonly=True, copy=False)
    approver_id = fields.Many2one('res.users', 'Diputuskan oleh', readonly=True, copy=False)
    review_note = fields.Text('Catatan Pemeriksaan', tracking=True, copy=False)
    decision_note = fields.Text('Alasan Keputusan', tracking=True, copy=False)
    release_date = fields.Date('Tanggal Rilis', tracking=True, copy=False)
    released_at = fields.Datetime('Waktu Rilis', readonly=True, copy=False)
    state = fields.Selection([
        ('draft', 'Draf'), ('review', 'Menunggu Pemeriksaan'), ('revision', 'Perlu Perbaikan'),
        ('approval', 'Menunggu Persetujuan'), ('approved', 'Menunggu Rilis'),
        ('rejected', 'Ditolak'), ('released', 'Sudah Dirilis'),
    ], 'Status', default='draft', required=True, readonly=True, tracking=True, copy=False)
    before_data = fields.Json('Data Sebelum Perubahan', readonly=True, copy=False)
    after_data = fields.Json('Data Setelah Rilis', readonly=True, copy=False)
    before_text = fields.Text('Data Berlaku saat Pengajuan', compute='_compute_comparison')
    proposed_text = fields.Text('Usulan / Hasil Rilis', compute='_compute_comparison')
    result_menu_id = fields.Many2one('kopitera.menu', 'Menu Hasil Rilis', readonly=True, copy=False)
    result_ingredient_id = fields.Many2one('kopitera.ingredient', 'Bahan Hasil Rilis', readonly=True, copy=False)
    is_author = fields.Boolean(compute='_compute_is_author')
    can_review = fields.Boolean(compute='_compute_is_author')

    _content_fields = {'kind', 'operation', 'division', 'menu_id', 'ingredient_id', 'proposed_name',
                       'description', 'allergens', 'unit', 'usage', 'reason'}
    _protected_fields = {'name', 'author_id', 'reviewer_id', 'approver_id', 'state', 'released_at',
                         'before_data', 'after_data', 'result_menu_id', 'result_ingredient_id'}

    @api.depends_context('uid')
    @api.depends('author_id')
    def _compute_is_author(self):
        for record in self:
            record.is_author = record.author_id == self.env.user
            record.can_review = not record.is_author and (self.env.user.has_group('kopitera_master.group_head_bar') or self.env.user.has_group('kopitera_master.group_head_kitchen'))

    @api.depends('before_data', 'after_data', 'kind', 'operation', 'division', 'proposed_name',
                 'description', 'allergens', 'unit', 'usage')
    def _compute_comparison(self):
        labels = {'name': 'Nama', 'division': 'Divisi / Area', 'description': 'Deskripsi',
                  'allergens': 'Alergen', 'unit': 'Satuan', 'active': 'Aktif', 'revision': 'Revisi Data'}
        def render(data):
            return '\n'.join('%s: %s' % (labels.get(key, key), value if value is not False else '-')
                             for key, value in data.items())
        for record in self:
            record.before_text = ('Data baru; belum ada data sebelumnya.' if record.operation == 'create'
                                  else render(record.before_data) if record.before_data
                                  else 'Snapshot data berlaku disimpan ketika pengajuan dikirim.')
            record.proposed_text = render(record.after_data or record._proposed_values())

    @api.onchange('kind')
    def _onchange_kind(self):
        self.menu_id = False
        self.ingredient_id = False

    @api.onchange('operation')
    def _onchange_operation(self):
        if self.operation == 'create':
            self.menu_id = False
            self.ingredient_id = False

    @api.onchange('menu_id', 'ingredient_id')
    def _onchange_target(self):
        target = self.menu_id if self.kind == 'menu' else self.ingredient_id
        if target:
            self.proposed_name = target.name
            if self.kind == 'menu':
                self.division = target.division
                self.description = target.description
                self.allergens = target.allergens
            else:
                self.unit = target.unit
                self.usage = target.division

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if (self._protected_fields | {'review_note', 'decision_note', 'release_date'}).intersection(vals) and not self.env.su:
                raise AccessError(_('Status dan keputusan hanya dapat diubah melalui alur pengajuan.'))
            vals.update(name=self.env['ir.sequence'].next_by_code('kopitera.master.change') or 'Baru',
                        author_id=self.env.uid, state='draft', reviewer_id=False, approver_id=False,
                        review_note=False, decision_note=False, release_date=False, released_at=False,
                        before_data=False, after_data=False, result_menu_id=False, result_ingredient_id=False)
        return super().create(vals_list)

    def _check_edit(self):
        self.check_access_rights('write')
        self.check_access_rule('write')
        for record in self:
            if record.state not in ('draft', 'revision'):
                raise UserError(_('Isi pengajuan hanya dapat diubah saat Draf atau Perlu Perbaikan.'))
            if record.author_id != self.env.user and not self.env.su:
                raise AccessError(_('Hanya pengaju yang dapat mengubah draf ini.'))

    def _check_step(self, state, group='group_editor'):
        self.check_access_rights('write')
        self.check_access_rule('write')
        if not self.env.su and not self.env.user.has_group('kopitera_master.' + group):
            raise AccessError(_('Peran Anda tidak diizinkan melakukan tindakan ini.'))
        if state == 'review' and not self.env.su and not (self.env.user.has_group('kopitera_master.group_head_bar') or self.env.user.has_group('kopitera_master.group_head_kitchen')):
            raise AccessError(_('Pemeriksaan teknis dilakukan oleh Head Bar atau Head Kitchen.'))
        if any(record.state != state for record in self):
            raise UserError(_('Status pengajuan tidak sesuai untuk tindakan ini.'))

    def _transition(self, vals):
        return super().write(vals)

    def write(self, vals):
        if self._protected_fields.intersection(vals) and not self.env.su:
            raise AccessError(_('Gunakan tombol alur pengajuan untuk mengubah status atau hasil rilis.'))
        if self._content_fields.intersection(vals):
            self._check_edit()
        if 'review_note' in vals:
            self._check_step('review')
            if any(record.author_id == self.env.user for record in self):
                raise UserError(_('Pengaju tidak dapat memeriksa pengajuannya sendiri.'))
        if {'decision_note', 'release_date'}.intersection(vals):
            self._check_step('approval', 'group_manager')
        return super().write(vals)

    def unlink(self):
        self._check_edit()
        return super().unlink()

    def _target(self):
        self.ensure_one()
        return self.menu_id if self.kind == 'menu' else self.ingredient_id

    def _snapshot(self):
        self.ensure_one()
        target = self._target()
        if not target:
            return {}
        names = ['name', 'division', 'active', 'revision']
        names += ['description', 'allergens'] if self.kind == 'menu' else ['unit']
        return {name: target[name] for name in names}

    def _proposed_values(self):
        self.ensure_one()
        if self.operation == 'deactivate':
            return {'active': False}
        vals = {'name': (self.proposed_name or '').strip()}
        if self.kind == 'menu':
            vals.update(division=self.division, description=self.description or False, allergens=self.allergens or False)
        else:
            vals.update(division=self.usage, unit=self.unit)
        return vals

    def _validate_proposal(self):
        self.ensure_one()
        if not (self.reason or '').strip():
            raise ValidationError(_('Alasan pengajuan wajib diisi.'))
        target = self._target()
        if self.operation == 'create':
            if self.menu_id or self.ingredient_id:
                raise ValidationError(_('Pengajuan baru tidak menggunakan data tujuan yang sudah ada.'))
        else:
            if not target or not target.exists():
                raise ValidationError(_('Pilih data tujuan yang akan diubah atau dinonaktifkan.'))
            target.check_access_rights('read')
            target.check_access_rule('read')
            if not target.active:
                raise ValidationError(_('Data tujuan sudah tidak aktif.'))
            if target.division not in (self.division, 'shared'):
                raise ValidationError(_('Divisi pengaju harus sesuai dengan data tujuan.'))
        if (self.kind == 'menu' and self.ingredient_id) or (self.kind == 'ingredient' and self.menu_id):
            raise ValidationError(_('Jenis data dan referensi tujuan tidak sesuai.'))
        if self.operation != 'deactivate':
            if not (self.proposed_name or '').strip():
                raise ValidationError(_('Nama yang diusulkan wajib diisi.'))
            if self.kind == 'ingredient':
                if not self.unit or self.usage not in (self.division, 'shared'):
                    raise ValidationError(_('Pilih satuan dan area penggunaan yang sesuai divisi pengaju.'))
                if target:
                    target._validate_reference_change(self._proposed_values())
        if self.operation == 'deactivate' and self.kind == 'ingredient':
            target._validate_reference_change({'active': False})

    def _notify(self, group, summary):
        for record in self:
            target_group = 'group_head_' + record.division if group == 'group_editor' else group
            users = self.env.ref('kopitera_master.' + target_group).sudo().users
            for user in users.filtered(lambda u: u.active and u.id != self.env.uid):
                if record.with_user(user).search_count([('id', '=', record.id)]):
                    record.activity_schedule('mail.mail_activity_data_todo', user_id=user.id, summary=summary)

    def _finish_activities(self):
        self.activity_ids.action_feedback(feedback=_('Tahap pengajuan sudah diproses.'))

    def action_submit(self):
        self._check_edit()
        for record in self:
            record._validate_proposal()
            record._transition({'before_data': record._snapshot(), 'state': 'review',
                                'reviewer_id': False, 'approver_id': False, 'review_note': False,
                                'decision_note': False, 'release_date': False})
        self._finish_activities()
        self._notify('group_editor', _('Periksa pengajuan menu / bahan baku'))
        return True

    def action_review(self):
        self._check_step('review')
        if any(record.author_id == self.env.user or not (record.review_note or '').strip() for record in self):
            raise ValidationError(_('Pemeriksa harus berbeda dari pengaju dan catatan pemeriksaan wajib diisi.'))
        self._transition({'state': 'approval', 'reviewer_id': self.env.uid})
        self._finish_activities()
        self._notify('group_manager', _('Putuskan pengajuan menu / bahan baku'))
        return True

    def action_return(self):
        self._check_step('review')
        if any(record.author_id == self.env.user or not (record.review_note or '').strip() for record in self):
            raise ValidationError(_('Pemeriksa harus berbeda dari pengaju dan catatan perbaikan wajib diisi.'))
        self._transition({'state': 'revision', 'reviewer_id': self.env.uid})
        self._finish_activities()
        for record in self:
            record.activity_schedule('mail.mail_activity_data_todo', user_id=record.author_id.id, summary=_('Perbaiki pengajuan menu / bahan'))
        return True

    def action_approve(self):
        self._check_step('approval', 'group_manager')
        if any(not record.release_date or not (record.decision_note or '').strip() for record in self):
            raise ValidationError(_('Tanggal rilis dan alasan keputusan wajib diisi.'))
        self._transition({'state': 'approved', 'approver_id': self.env.uid})
        self._finish_activities()
        self._notify('group_manager', _('Rilis pengajuan menu / bahan pada tanggal yang ditetapkan'))
        return True

    def action_reject(self):
        self._check_step('approval', 'group_manager')
        if any(not (record.decision_note or '').strip() for record in self):
            raise ValidationError(_('Alasan penolakan wajib diisi.'))
        self._transition({'state': 'rejected', 'approver_id': self.env.uid})
        self._finish_activities()
        return True

    def action_request_update(self):
        self._check_step('approved', 'group_manager')
        self._transition({'state': 'revision'})
        self._finish_activities()
        for record in self:
            record.message_post(body=_('Manager meminta pembaruan draf. Pemeriksaan dan persetujuan harus diulang sebelum rilis.'))
            record.activity_schedule('mail.mail_activity_data_todo', user_id=record.author_id.id, summary=_('Perbarui pengajuan sebelum diajukan kembali'))
        return True

    def action_release(self):
        self._check_step('approved', 'group_manager')
        for record in self:
            if not record.release_date or record.release_date > fields.Date.context_today(record):
                raise UserError(_('Pengajuan baru dapat dirilis pada atau setelah tanggal rilis.'))
            target = record._target()
            if target:
                # Table names come from fixed model metadata; no user-provided SQL identifiers.
                table = 'kopitera_menu' if record.kind == 'menu' else 'kopitera_ingredient'
                self.env.cr.execute('SELECT id FROM ' + table + ' WHERE id = %s FOR UPDATE', [target.id])
                target.invalidate_recordset()
                if record.before_data != record._snapshot():
                    raise UserError(_('Data tujuan telah berubah sejak pengajuan dikirim. Gunakan Minta Pembaruan, periksa kembali draf, lalu ulangi persetujuan.'))
            record._validate_proposal()
            values = record._proposed_values()
            if record.operation == 'create':
                model = 'kopitera.menu' if record.kind == 'menu' else 'kopitera.ingredient'
                target = self.env[model].sudo().create(values)
            else:
                target.sudo().write(values)
            names = ['name', 'division', 'active', 'revision'] + (['description', 'allergens'] if record.kind == 'menu' else ['unit'])
            record._transition({
                'state': 'released', 'released_at': fields.Datetime.now(),
                'result_menu_id': target.id if record.kind == 'menu' else False,
                'result_ingredient_id': target.id if record.kind == 'ingredient' else False,
                'after_data': {name: target[name] for name in names},
            })
            record.message_post(body=_('Perubahan data telah dirilis. Snapshot sebelum dan sesudah tersimpan pada pengajuan ini.'))
        self._finish_activities()
        return True


class MenuLifecycle(models.Model):
    _inherit = 'kopitera.menu'

    active = fields.Boolean('Aktif', default=True)
    revision = fields.Integer('Revisi Data', default=1, readonly=True)

    def write(self, vals):
        business = {'name', 'division', 'description', 'allergens', 'active'}
        if business.intersection(vals):
            for record in self:
                if 'division' in vals and vals['division'] != record.division and self.env['kopitera.recipe'].sudo().search_count([('menu_id', '=', record.id)]):
                    raise ValidationError(_('Divisi menu yang sudah memiliki resep tidak dapat diubah.'))
                if vals.get('active') is False and record.current_recipe_id:
                    record.current_recipe_id.sudo()._transition({'state': 'archived'})
                values = dict(vals, revision=record.revision + 1)
                if vals.get('active') is False:
                    values['current_recipe_id'] = False
                super(MenuLifecycle, record).write(values)
            return True
        return super().write(vals)

    def action_propose_change(self):
        self.ensure_one()
        self.check_access_rights('read')
        self.check_access_rule('read')
        proposal = self.env['kopitera.master.change'].create({
            'kind': 'menu', 'operation': 'update', 'division': self.division, 'menu_id': self.id,
            'proposed_name': self.name, 'description': self.description, 'allergens': self.allergens,
        })
        return {'type': 'ir.actions.act_window', 'name': _('Pengajuan Menu'),
                'res_model': proposal._name, 'res_id': proposal.id, 'view_mode': 'form'}

    def action_propose_recipe(self):
        if any(not record.active for record in self):
            raise ValidationError(_('Menu nonaktif tidak dapat digunakan untuk pengajuan resep.'))
        return super().action_propose_recipe()


class IngredientLifecycle(models.Model):
    _inherit = 'kopitera.ingredient'

    active = fields.Boolean('Aktif', default=True)
    revision = fields.Integer('Revisi Data', default=1, readonly=True)

    def _validate_reference_change(self, vals):
        lines = self.env['kopitera.recipe.line'].sudo()
        for record in self:
            if 'unit' in vals and vals['unit'] != record.unit and lines.search_count([('ingredient_id', '=', record.id)]):
                raise ValidationError(_('Satuan bahan yang sudah dipakai resep tidak dapat diubah. Ajukan bahan baru dengan satuan yang benar.'))
            if vals.get('active') is False and lines.search_count([('ingredient_id', '=', record.id), ('recipe_id.state', '=', 'published')]):
                raise ValidationError(_('Bahan masih digunakan oleh resep berlaku dan tidak dapat dinonaktifkan.'))
            if 'division' in vals and vals['division'] != 'shared' and lines.search_count([
                ('ingredient_id', '=', record.id), ('recipe_id.state', '=', 'published'),
                ('recipe_id.division', '!=', vals['division']),
            ]):
                raise ValidationError(_('Area penggunaan tidak boleh mengecualikan divisi resep yang sedang berlaku.'))

    def write(self, vals):
        self._validate_reference_change(vals)
        if {'name', 'unit', 'division', 'active'}.intersection(vals):
            for record in self:
                super(IngredientLifecycle, record).write(dict(vals, revision=record.revision + 1))
            return True
        return super().write(vals)

    def action_propose_change(self):
        self.ensure_one()
        self.check_access_rights('read')
        self.check_access_rule('read')
        division = self.division if self.division != 'shared' else ('kitchen' if self.env.user.has_group('kopitera_master.group_head_kitchen') else 'bar')
        proposal = self.env['kopitera.master.change'].create({
            'kind': 'ingredient', 'operation': 'update', 'division': division, 'ingredient_id': self.id,
            'proposed_name': self.name, 'unit': self.unit, 'usage': self.division,
        })
        return {'type': 'ir.actions.act_window', 'name': _('Pengajuan Bahan Baku'),
                'res_model': proposal._name, 'res_id': proposal.id, 'view_mode': 'form'}


class RecipeLifecycle(models.Model):
    _inherit = 'kopitera.recipe'

    can_review = fields.Boolean(compute='_compute_can_review')

    @api.depends_context('uid')
    @api.depends('author_id')
    def _compute_can_review(self):
        for record in self:
            record.can_review = record.author_id != self.env.user and (self.env.user.has_group('kopitera_master.group_head_bar') or self.env.user.has_group('kopitera_master.group_head_kitchen'))

    def _check_step(self, state, group):
        super()._check_step(state, group)
        if state == 'review' and not self.env.su and not (self.env.user.has_group('kopitera_master.group_head_bar') or self.env.user.has_group('kopitera_master.group_head_kitchen')):
            raise AccessError(_('Pemeriksaan teknis dilakukan oleh Head Bar atau Head Kitchen.'))

    def _notify_group(self, group_xmlid, summary):
        if group_xmlid == 'group_editor':
            for record in self:
                super(RecipeLifecycle, record)._notify_group('group_head_' + record.division, summary)
        else:
            super()._notify_group(group_xmlid, summary)

    def _check_live_references(self):
        for record in self:
            if not record.menu_id.active:
                raise ValidationError(_('Menu sudah nonaktif. Resep tidak dapat diajukan atau dirilis.'))
            for line in record.line_ids:
                if not line.ingredient_id.active:
                    raise ValidationError(_('Resep menggunakan bahan yang sudah nonaktif. Perbarui draf terlebih dahulu.'))
            record.line_ids._check_division()

    def action_submit(self):
        self._check_content_edit()
        self._check_live_references()
        self._transition({'reviewer_id': False, 'approver_id': False, 'review_note': False,
                          'decision_note': False, 'release_date': False})
        return super().action_submit()

    def action_release(self):
        self._check_step('approved', 'group_manager')
        for record in self.sorted('menu_id'):
            self.env.cr.execute('SELECT id FROM kopitera_menu WHERE id = %s FOR UPDATE', [record.menu_id.id])
        ingredients = self.mapped('line_ids.ingredient_id')
        if ingredients:
            self.env.cr.execute('SELECT id FROM kopitera_ingredient WHERE id IN %s ORDER BY id FOR UPDATE', [tuple(ingredients.ids)])
            ingredients.invalidate_recordset()
        self.mapped('menu_id').invalidate_recordset()
        self._check_live_references()
        return super().action_release()

    def action_request_update(self):
        self._check_step('approved', 'group_manager')
        self._transition({'state': 'revision'})
        self._finish_activities()
        for record in self:
            record.message_post(body=_('Manager meminta pembaruan resep. Pemeriksaan dan persetujuan harus diulang.'))
            record.activity_schedule('mail.mail_activity_data_todo', user_id=record.author_id.id,
                                     summary=_('Perbarui resep sebelum diajukan kembali'))
        return True
