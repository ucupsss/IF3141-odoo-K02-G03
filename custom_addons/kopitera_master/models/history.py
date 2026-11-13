"""Audit log, notifikasi, perbandingan gramasi, dan pemulihan versi (UC-04, UC-07, UC-08, UC-12)."""
from markupsafe import Markup, escape

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError

from .recipe import DIVISIONS, to_base

UNIT_LABELS = {'g': 'g', 'kg': 'kg', 'ml': 'ml', 'l': 'L', 'pcs': 'buah'}

AUDIT_ACTIONS = [
    ('submit', 'Diajukan'),
    ('review', 'Lolos Pemeriksaan'),
    ('return', 'Dikembalikan untuk Perbaikan'),
    ('approve', 'Disetujui'),
    ('reject', 'Ditolak'),
    ('request_update', 'Diminta Pembaruan'),
    ('release', 'Dirilis'),
    ('restore', 'Pengajuan Pemulihan Versi'),
    ('import', 'Migrasi Data Awal'),
]

NOTIFICATION_KINDS = [
    ('review', 'Perlu Pemeriksaan'),
    ('revision', 'Perlu Perbaikan'),
    ('approval', 'Perlu Persetujuan'),
    ('approved', 'Disetujui'),
    ('rejected', 'Ditolak'),
    ('release', 'Dirilis'),
]


def composition_text(recipe):
    """Ringkasan komposisi satu versi resep untuk log audit."""
    if not recipe:
        return 'Belum ada resep berlaku.'
    lines = ['%s: %s %s' % (line.ingredient_id.name, _fmt(line.quantity), UNIT_LABELS.get(line.unit, line.unit or ''))
             for line in recipe.line_ids]
    if lines and recipe.portion_qty:
        lines.insert(0, 'Jumlah porsi: %s' % recipe.portion_qty)
    return '\n'.join(lines) or 'Belum ada komposisi.'


def _fmt(value):
    return ('%.3f' % value).rstrip('0').rstrip('.') if value is not None else '-'


class KopiteraAuditLog(models.Model):
    _name = 'kopitera.audit.log'
    _description = 'Log Audit Kopitera'
    _order = 'id desc'
    _rec_name = 'reference'

    timestamp = fields.Datetime('Waktu', default=fields.Datetime.now, readonly=True, required=True)
    user_id = fields.Many2one('res.users', 'Pelaku', readonly=True, required=True, ondelete='restrict')
    action = fields.Selection(AUDIT_ACTIONS, 'Jenis Tindakan', readonly=True, required=True)
    object_type = fields.Selection([('recipe', 'Resep'), ('menu', 'Menu'), ('ingredient', 'Bahan Baku')],
                                   'Jenis Data', readonly=True, required=True)
    reference = fields.Char('Nomor Pengajuan', readonly=True)
    object_name = fields.Char('Nama Data', readonly=True)
    division = fields.Selection(DIVISIONS, 'Divisi', readonly=True)
    recipe_id = fields.Many2one('kopitera.recipe', 'Pengajuan Resep', readonly=True, ondelete='cascade', index=True)
    change_id = fields.Many2one('kopitera.master.change', 'Pengajuan Menu/Bahan', readonly=True, ondelete='cascade', index=True)
    before_value = fields.Text('Nilai Sebelum', readonly=True)
    after_value = fields.Text('Nilai Sesudah', readonly=True)
    note = fields.Text('Catatan', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            raise AccessError(_('Log audit hanya dibuat otomatis oleh sistem.'))
        return super().create(vals_list)

    def write(self, vals):
        raise AccessError(_('Log audit bersifat permanen dan tidak dapat diubah.'))

    def unlink(self):
        raise AccessError(_('Log audit bersifat permanen dan tidak dapat dihapus.'))

    def action_open_source(self):
        self.ensure_one()
        record = self.recipe_id or self.change_id
        if not record:
            raise UserError(_('Log ini tidak terkait pengajuan.'))
        return {'type': 'ir.actions.act_window', 'res_model': record._name, 'res_id': record.id, 'view_mode': 'form'}


class KopiteraNotification(models.Model):
    _name = 'kopitera.notification'
    _description = 'Notifikasi Kopitera'
    _order = 'is_read, id desc'

    name = fields.Char('Judul', readonly=True, required=True)
    message = fields.Text('Isi Notifikasi', readonly=True)
    kind = fields.Selection(NOTIFICATION_KINDS, 'Jenis', readonly=True, required=True)
    user_id = fields.Many2one('res.users', 'Penerima', readonly=True, required=True, index=True, ondelete='cascade')
    recipe_id = fields.Many2one('kopitera.recipe', 'Pengajuan Resep', readonly=True, ondelete='cascade')
    change_id = fields.Many2one('kopitera.master.change', 'Pengajuan Menu/Bahan', readonly=True, ondelete='cascade')
    reference = fields.Char('Nomor', readonly=True)
    is_read = fields.Boolean('Sudah Dibaca', readonly=True, default=False)
    create_date = fields.Datetime('Waktu Dibuat', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            raise AccessError(_('Notifikasi hanya dibuat otomatis oleh sistem.'))
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.su and (set(vals) - {'is_read'} or any(r.user_id != self.env.user for r in self)):
            raise AccessError(_('Notifikasi hanya dapat ditandai dibaca oleh penerimanya.'))
        return super().write(vals)

    def unlink(self):
        if not self.env.su:
            raise AccessError(_('Notifikasi tidak dapat dihapus.'))
        return super().unlink()

    def action_mark_read(self):
        self.write({'is_read': True})
        return True

    def action_open(self):
        self.ensure_one()
        self.write({'is_read': True})
        record = self.recipe_id or self.change_id
        return {'type': 'ir.actions.act_window', 'res_model': record._name, 'res_id': record.id, 'view_mode': 'form'}

    @api.model
    def _send(self, users, kind, title, message, record):
        """Buat notifikasi bagi penerima yang memang dapat membaca record terkait."""
        vals = []
        for user in users.filtered(lambda u: u.active):
            as_user = record.with_user(user)
            if not as_user.check_access_rights('read', raise_exception=False) or not as_user.search_count([('id', '=', record.id)]):
                continue
            vals.append({
                'user_id': user.id, 'kind': kind, 'name': title, 'message': message,
                'reference': record.name,
                'recipe_id': record.id if record._name == 'kopitera.recipe' else False,
                'change_id': record.id if record._name == 'kopitera.master.change' else False,
            })
        if vals:
            self.sudo().create(vals)


class KopiteraWorkflowEvents(models.AbstractModel):
    """Penerima notifikasi dan pencatatan log yang dipakai bersama oleh pengajuan resep dan menu/bahan."""
    _name = 'kopitera.workflow.events'
    _description = 'Peristiwa Alur Pengajuan Kopitera'

    def _kp_group_users(self, xmlid):
        return self.env.ref('kopitera_master.' + xmlid).sudo().users

    def _kp_heads(self):
        self.ensure_one()
        return self._kp_group_users('group_head_' + self.division)

    def _kp_object_info(self):
        raise NotImplementedError

    def _kp_log(self, action, before=None, after=None, note=None):
        for record in self:
            object_type, object_name = record._kp_object_info()
            self.env['kopitera.audit.log'].sudo().create({
                'user_id': self.env.uid, 'action': action, 'object_type': object_type,
                'object_name': object_name, 'reference': record.name, 'division': record.division,
                'recipe_id': record.id if record._name == 'kopitera.recipe' else False,
                'change_id': record.id if record._name == 'kopitera.master.change' else False,
                'before_value': before if before is not None else record._kp_before_text(),
                'after_value': after if after is not None else record._kp_after_text(),
                'note': note,
            })

    def _kp_notify(self, users, kind, title, message):
        Notification = self.env['kopitera.notification']
        for record in self:
            Notification._send(users.filtered(lambda u: u.id != self.env.uid), kind, title % record.name,
                               message, record)

    def _kp_dispatch(self, action):
        """Notifikasi UC-12 sesuai FR-09: pemeriksa, pengaju, Manager Area, dan Head Floor saat rilis."""
        for record in self:
            label = record._kp_object_info()[1]
            author = record.author_id
            if action == 'submit':
                record._kp_notify(record._kp_heads(), 'review', _('%s perlu diperiksa'),
                                  _('Pengajuan %s dari %s menunggu pemeriksaan teknis.') % (label, author.name))
            elif action == 'review':
                record._kp_notify(record._kp_group_users('group_manager'), 'approval', _('%s perlu persetujuan'),
                                  _('Pengajuan %s telah lolos pemeriksaan dan menunggu keputusan Manager Area.') % label)
            elif action == 'return':
                record._kp_notify(author, 'revision', _('%s perlu diperbaiki'),
                                  _('Catatan pemeriksa: %s') % (record.review_note or '-'))
            elif action == 'request_update':
                record._kp_notify(author, 'revision', _('%s perlu diperbarui'),
                                  _('Manager Area meminta pembaruan sebelum rilis. Pemeriksaan dan persetujuan diulang.'))
            elif action == 'approve':
                record._kp_notify(author, 'approved', _('%s disetujui'),
                                  _('Pengajuan %s disetujui dengan tanggal rilis %s.') % (label, record.release_date))
            elif action == 'reject':
                record._kp_notify(author, 'rejected', _('%s ditolak'),
                                  _('Alasan penolakan: %s') % (record.decision_note or '-'))
            elif action == 'release':
                receivers = author | record._kp_heads() | record._kp_group_users('group_head_floor')
                record._kp_notify(receivers, 'release', _('%s telah dirilis'),
                                  _('%s kini berlaku di seluruh cabang. Head Floor mohon menyampaikan perubahan kepada Staf Floor '
                                    'dan mencocokkan daftar menu dRetail.') % label)


class RecipeHistory(models.Model):
    _name = 'kopitera.recipe'
    _inherit = ['kopitera.recipe', 'kopitera.workflow.events']

    previous_recipe_id = fields.Many2one('kopitera.recipe', 'Versi Sebelumnya', readonly=True, copy=False)
    restored_from_id = fields.Many2one('kopitera.recipe', 'Dipulihkan dari Versi', readonly=True, copy=False)
    comparison_html = fields.Html('Perbandingan Gramasi', compute='_compute_comparison_html', sanitize=False)
    comparison_label = fields.Char(compute='_compute_comparison_html')
    audit_log_ids = fields.One2many('kopitera.audit.log', 'recipe_id', 'Log Audit', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('restored_from_id') and not self.env.context.get('kopitera_restore'):
                raise AccessError(_('Pemulihan versi hanya dapat dibuat melalui formulir pemulihan.'))
            if vals.get('previous_recipe_id') and not self.env.su:
                raise AccessError(_('Versi sebelumnya ditetapkan sistem saat rilis.'))
        return super().create(vals_list)

    def write(self, vals):
        if {'previous_recipe_id', 'restored_from_id'}.intersection(vals) and not self.env.su:
            raise AccessError(_('Relasi versi ditetapkan oleh sistem.'))
        return super().write(vals)

    def _kp_object_info(self):
        return 'recipe', self.menu_id.name

    def _kp_base_recipe(self):
        """Versi pembanding: versi sebelumnya untuk resep yang sudah dirilis, versi berlaku untuk pengajuan."""
        self.ensure_one()
        if self.state in ('published', 'archived'):
            return self.previous_recipe_id
        current = self.menu_id.sudo().current_recipe_id
        return current if current != self else self.browse()

    def _kp_before_text(self):
        return composition_text(self._kp_base_recipe().sudo())

    def _kp_after_text(self):
        return composition_text(self)

    @api.depends('line_ids.quantity', 'line_ids.unit', 'line_ids.ingredient_id', 'state', 'menu_id', 'previous_recipe_id')
    @api.depends_context('uid')
    def _compute_comparison_html(self):
        for record in self:
            base = record._kp_base_recipe().sudo()
            record.comparison_label = (_('Dibandingkan dengan versi %s (versi sebelumnya)') % base.version
                                       if record.state in ('published', 'archived') and base
                                       else _('Dibandingkan dengan versi %s yang sedang berlaku') % base.version if base
                                       else _('Belum ada versi pembanding; seluruh bahan merupakan tambahan.'))
            record.comparison_html = self._kp_comparison_table(base.line_ids, record.line_ids,
                                                              _('Takaran Pembanding'), _('Takaran Versi Ini'))

    @api.model
    def _kp_comparison_table(self, old_lines, new_lines, old_label, new_label):
        old = {line.ingredient_id.id: line for line in old_lines}
        new = {line.ingredient_id.id: line for line in new_lines}
        order = [line.ingredient_id.id for line in new_lines] + [key for key in old if key not in new]
        rows = []
        for key in order:
            before, after = old.get(key), new.get(key)
            line = after or before
            # Dibandingkan dalam satuan baku bahan, sehingga 0,2 kg dan 200 g dianggap sama (FR-04).
            qty_before = to_base(before.quantity, before.unit, before.ingredient_id.unit) if before else 0.0
            qty_after = to_base(after.quantity, after.unit, after.ingredient_id.unit) if after else 0.0
            if before and after:
                diff = qty_after - qty_before
                status, css = ((_('Tetap'), '') if abs(diff) < 1e-9 else
                               (_('Bertambah'), 'table-warning') if diff > 0 else (_('Berkurang'), 'table-warning'))
                diff_text = '%+g' % diff if abs(diff) >= 1e-9 else '0'
            elif after:
                status, css, diff_text = _('Bahan Baru'), 'table-success', '+' + _fmt(qty_after)
            else:
                status, css, diff_text = _('Dihapus'), 'table-danger', '-' + _fmt(qty_before)
            unit = UNIT_LABELS.get(line.ingredient_id.unit, line.ingredient_id.unit or '')
            rows.append(Markup('<tr class="%s"><td>%s</td><td>%s</td><td class="text-end">%s</td>'
                               '<td class="text-end">%s</td><td class="text-end">%s</td><td>%s</td></tr>') % (
                css, line.ingredient_id.name, unit, _fmt(qty_before) if before else '-',
                _fmt(qty_after) if after else '-', diff_text, status))
        if not rows:
            rows.append(Markup('<tr><td colspan="6" class="text-muted">Belum ada komposisi.</td></tr>'))
        head = Markup('<table class="table table-sm table-bordered o_kopitera_compare"><thead class="table-light"><tr>'
                      '<th>Bahan Baku</th><th>Satuan</th><th class="text-end">%s</th><th class="text-end">%s</th>'
                      '<th class="text-end">Selisih</th><th>Keterangan</th></tr></thead><tbody>') % (old_label, new_label)
        return head + Markup('').join(rows) + Markup('</tbody></table>')

    # --- alur: log audit + notifikasi -------------------------------------------------
    def action_submit(self):
        result = super().action_submit()
        for record in self:
            record._kp_log('submit', note=_('Alasan: %s') % (record.reason or '-'))
        self._kp_dispatch('submit')
        return result

    def action_review(self):
        result = super().action_review()
        for record in self:
            record._kp_log('review', note=record.review_note)
        self._kp_dispatch('review')
        return result

    def action_return(self):
        result = super().action_return()
        for record in self:
            record._kp_log('return', note=record.review_note)
        self._kp_dispatch('return')
        return result

    def action_approve(self):
        result = super().action_approve()
        for record in self:
            record._kp_log('approve', note=_('%s — tanggal rilis %s') % (record.decision_note, record.release_date))
        self._kp_dispatch('approve')
        return result

    def action_reject(self):
        result = super().action_reject()
        for record in self:
            record._kp_log('reject', note=record.decision_note)
        self._kp_dispatch('reject')
        return result

    def action_request_update(self):
        result = super().action_request_update()
        self._kp_log('request_update')
        self._kp_dispatch('request_update')
        return result

    def action_release(self):
        previous = {record.id: record.menu_id.sudo().current_recipe_id for record in self}
        before = {record.id: composition_text(previous[record.id].sudo()) for record in self}
        result = super().action_release()
        for record in self:
            if previous[record.id]:
                record.sudo().write({'previous_recipe_id': previous[record.id].id})
            record._kp_log('release', before=before[record.id], after=composition_text(record),
                           note=_('Versi %s berlaku di seluruh cabang.') % record.version)
        self._kp_dispatch('release')
        return result

    def action_open_restore(self):
        self.ensure_one()
        if not self.env.user.has_group('kopitera_master.group_manager'):
            raise AccessError(_('Pemulihan versi hanya dapat diajukan Manager Area.'))
        if self.state != 'archived':
            raise UserError(_('Hanya versi arsip yang dapat dipulihkan.'))
        return {'type': 'ir.actions.act_window', 'name': _('Pulihkan Versi Resep'), 'res_model': 'kopitera.restore.wizard',
                'view_mode': 'form', 'target': 'new', 'context': {'default_recipe_id': self.id}}


class RestoreWizard(models.TransientModel):
    _name = 'kopitera.restore.wizard'
    _description = 'Pemulihan Versi Resep'

    recipe_id = fields.Many2one('kopitera.recipe', 'Versi Tujuan', required=True, readonly=True)
    menu_id = fields.Many2one(related='recipe_id.menu_id', string='Menu')
    target_version = fields.Integer(related='recipe_id.version', string='Nomor Versi Tujuan')
    current_version = fields.Integer('Versi Berlaku', compute='_compute_preview')
    reason = fields.Text('Alasan Pemulihan', required=True)
    preview_html = fields.Html('Perbandingan', compute='_compute_preview', sanitize=False)

    @api.depends('recipe_id')
    def _compute_preview(self):
        Recipe = self.env['kopitera.recipe']
        for wizard in self:
            current = wizard.recipe_id.menu_id.sudo().current_recipe_id
            wizard.current_version = current.version
            wizard.preview_html = Recipe._kp_comparison_table(current.line_ids, wizard.recipe_id.line_ids,
                                                              _('Versi Berlaku'), _('Versi Tujuan'))

    def action_confirm(self):
        self.ensure_one()
        if not self.env.user.has_group('kopitera_master.group_manager'):
            raise AccessError(_('Pemulihan versi hanya dapat diajukan Manager Area.'))
        target = self.recipe_id
        if target.state != 'archived':
            raise UserError(_('Hanya versi arsip yang dapat dipulihkan.'))
        if not (self.reason or '').strip():
            raise ValidationError(_('Alasan pemulihan wajib diisi.'))
        open_states = ['draft', 'review', 'revision', 'approval', 'approved']
        if self.env['kopitera.recipe'].sudo().search_count([('menu_id', '=', target.menu_id.id),
                                                            ('restored_from_id', '!=', False),
                                                            ('state', 'in', open_states)]):
            raise UserError(_('Masih ada pengajuan pemulihan yang belum selesai untuk menu ini.'))
        proposal = self.env['kopitera.recipe'].with_context(kopitera_restore=True).create({
            'menu_id': target.menu_id.id,
            'restored_from_id': target.id,
            'instructions': target.instructions,
            'portion_qty': target.portion_qty or 1,
            'reason': _('Pemulihan ke versi %s. %s') % (target.version, self.reason.strip()),
            'line_ids': [(0, 0, {'ingredient_id': line.ingredient_id.id, 'quantity': line.quantity, 'unit': line.unit})
                         for line in target.line_ids],
        })
        proposal._kp_log('restore', before=composition_text(target.menu_id.sudo().current_recipe_id),
                         after=composition_text(proposal), note=self.reason.strip())
        proposal.action_submit()
        return {'type': 'ir.actions.act_window', 'res_model': 'kopitera.recipe', 'res_id': proposal.id, 'view_mode': 'form'}


class MasterChangeHistory(models.Model):
    _name = 'kopitera.master.change'
    _inherit = ['kopitera.master.change', 'kopitera.workflow.events']

    audit_log_ids = fields.One2many('kopitera.audit.log', 'change_id', 'Log Audit', readonly=True)

    def _kp_object_info(self):
        name = self.proposed_name or (self.menu_id or self.ingredient_id).name or self.name
        return self.kind, name

    def _kp_before_text(self):
        return self.before_text

    def _kp_after_text(self):
        return self.proposed_text

    def action_submit(self):
        result = super().action_submit()
        for record in self:
            record._kp_log('submit', note=_('%s — alasan: %s') % (dict(record._fields['operation'].selection)[record.operation], record.reason))
        self._kp_dispatch('submit')
        return result

    def action_review(self):
        result = super().action_review()
        for record in self:
            record._kp_log('review', note=record.review_note)
        self._kp_dispatch('review')
        return result

    def action_return(self):
        result = super().action_return()
        for record in self:
            record._kp_log('return', note=record.review_note)
        self._kp_dispatch('return')
        return result

    def action_approve(self):
        result = super().action_approve()
        for record in self:
            record._kp_log('approve', note=_('%s — tanggal rilis %s') % (record.decision_note, record.release_date))
        self._kp_dispatch('approve')
        return result

    def action_reject(self):
        result = super().action_reject()
        for record in self:
            record._kp_log('reject', note=record.decision_note)
        self._kp_dispatch('reject')
        return result

    def action_request_update(self):
        result = super().action_request_update()
        self._kp_log('request_update')
        self._kp_dispatch('request_update')
        return result

    def action_release(self):
        result = super().action_release()
        for record in self:
            record._kp_log('release', note=_('Data berlaku diperbarui di seluruh cabang.'))
        self._kp_dispatch('release')
        return result
