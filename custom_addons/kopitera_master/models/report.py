"""Laporan rekap katalog, lembar resep, dan riwayat pembaruan (UC-11, FR-12)."""
import base64
import io

from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .history import AUDIT_ACTIONS, UNIT_LABELS, _fmt

try:
    import xlsxwriter
except ImportError:  # pragma: no cover - xlsxwriter selalu ada pada image odoo:17
    xlsxwriter = None

REPORT_TYPES = [
    ('catalog', 'Rekap Katalog Menu Aktif'),
    ('recipe', 'Lembar Resep per Menu'),
    ('history', 'Rekap Riwayat Pembaruan'),
]


class KopiteraReportWizard(models.TransientModel):
    _name = 'kopitera.report.wizard'
    _description = 'Laporan Rekap Kopitera'

    report_type = fields.Selection(REPORT_TYPES, 'Jenis Laporan', required=True, default='catalog')
    division = fields.Selection([('all', 'Semua divisi yang dapat diakses'), ('bar', 'Minuman / Bar'),
                                 ('kitchen', 'Makanan / Kitchen')], 'Kategori', required=True, default='all')
    menu_ids = fields.Many2many('kopitera.menu', string='Menu', help='Kosongkan untuk semua menu yang memiliki resep berlaku.')
    menu_status = fields.Selection([('active', 'Aktif'), ('inactive', 'Nonaktif'), ('all', 'Semua')],
                                   'Status Menu', default='active', required=True)
    history_action = fields.Selection([('all', 'Semua tindakan')] + AUDIT_ACTIONS, 'Tindakan', default='all', required=True)
    date_from = fields.Date('Dari Tanggal')
    date_to = fields.Date('Sampai Tanggal')
    output_format = fields.Selection([('pdf', 'PDF'), ('xlsx', 'Excel (.xlsx)')], 'Format Berkas', default='pdf', required=True)
    preview_html = fields.Html('Pratinjau', compute='_compute_preview', sanitize=False)
    file_data = fields.Binary('Berkas', readonly=True, attachment=False)
    file_name = fields.Char('Nama Berkas', readonly=True)

    # ------------------------------------------------------------------ data
    def _division_domain(self, field='division'):
        return [] if self.division == 'all' else [(field, '=', self.division)]

    def _title(self):
        return dict(REPORT_TYPES)[self.report_type]

    def _filter_text(self):
        parts = [_('Kategori: %s') % dict(self._fields['division'].selection)[self.division]]
        if self.report_type == 'catalog':
            parts.append(_('Status: %s') % dict(self._fields['menu_status'].selection)[self.menu_status])
        if self.report_type == 'recipe' and self.menu_ids:
            parts.append(_('Menu: %s') % ', '.join(self.menu_ids.mapped('name')))
        if self.report_type == 'history':
            parts.append(_('Tindakan: %s') % dict(self._fields['history_action'].selection)[self.history_action])
            parts.append(_('Periode: %s s.d. %s') % (self.date_from or _('awal'), self.date_to or _('sekarang')))
        return ' | '.join(parts)

    def _catalog_rows(self):
        Menu = self.env['kopitera.menu'].with_context(active_test=False)
        domain = self._division_domain()
        if self.menu_status != 'all':
            domain.append(('active', '=', self.menu_status == 'active'))
        rows = []
        for menu in Menu.search(domain, order='division, name'):
            recipe = menu.current_recipe_id
            rows.append([menu.name, dict(menu._fields['division'].selection)[menu.division], menu.allergens or '-',
                         'Aktif' if menu.active else 'Nonaktif', recipe.version or '-',
                         fields.Datetime.to_string(recipe.released_at)[:10] if recipe.released_at else '-',
                         len(recipe.line_ids)])
        return [_('Nama Menu'), _('Kategori'), _('Alergen'), _('Status'), _('Versi Resep'), _('Tanggal Berlaku'), _('Jumlah Bahan')], rows

    def _recipes(self):
        domain = [('state', '=', 'published')] + self._division_domain()
        if self.menu_ids:
            domain.append(('menu_id', 'in', self.menu_ids.ids))
        return self.env['kopitera.recipe'].search(domain, order='division, menu_id')

    def _recipe_rows(self):
        rows = []
        for recipe in self._recipes():
            for line in recipe.line_ids:
                rows.append([recipe.menu_id.name, recipe.version,
                             fields.Datetime.to_string(recipe.released_at)[:10] if recipe.released_at else '-',
                             line.ingredient_id.name, _fmt(line.quantity), UNIT_LABELS.get(line.unit, line.unit)])
        return [_('Menu'), _('Versi'), _('Berlaku Sejak'), _('Bahan Baku'), _('Takaran per Porsi'), _('Satuan')], rows

    def _history_logs(self):
        domain = self._division_domain()
        if self.history_action != 'all':
            domain.append(('action', '=', self.history_action))
        if self.date_from:
            domain.append(('timestamp', '>=', fields.Datetime.to_string(self.date_from)))
        if self.date_to:
            domain.append(('timestamp', '<', fields.Datetime.to_string(fields.Date.add(self.date_to, days=1))))
        return self.env['kopitera.audit.log'].search(domain, order='timestamp desc, id desc')

    def _history_rows(self):
        actions = dict(AUDIT_ACTIONS)
        types = dict(self.env['kopitera.audit.log']._fields['object_type'].selection)
        tz_ctx = self.with_context(tz=self.env.user.tz or 'Asia/Jakarta')
        rows = []
        for log in self._history_logs():
            stamp = fields.Datetime.context_timestamp(tz_ctx, log.timestamp).strftime('%Y-%m-%d %H:%M')
            rows.append([stamp, log.reference or '-', types.get(log.object_type), log.object_name or '-',
                         actions.get(log.action), log.user_id.name, (log.note or '').replace('\n', ' ')])
        return [_('Waktu'), _('Nomor'), _('Jenis Data'), _('Nama Data'), _('Tindakan'), _('Pelaku'), _('Catatan')], rows

    def _get_table(self):
        self.ensure_one()
        return getattr(self, '_%s_rows' % self.report_type)()

    # --------------------------------------------------------------- preview
    @api.depends('report_type', 'division', 'menu_ids', 'menu_status', 'history_action', 'date_from', 'date_to')
    def _compute_preview(self):
        for wizard in self:
            if wizard.date_from and wizard.date_to and wizard.date_from > wizard.date_to:
                wizard.preview_html = Markup('<div class="alert alert-warning">Tanggal awal melebihi tanggal akhir.</div>')
                continue
            header, rows = wizard._get_table()
            body = Markup('').join(
                Markup('<tr>%s</tr>') % Markup('').join(Markup('<td>%s</td>') % cell for cell in row) for row in rows[:50])
            if not rows:
                body = Markup('<tr><td colspan="%s" class="text-muted">Tidak ada data sesuai filter.</td></tr>') % len(header)
            note = Markup('<p class="text-muted small">Menampilkan %s dari %s baris.</p>') % (min(len(rows), 50), len(rows))
            wizard.preview_html = (Markup('<table class="table table-sm table-bordered"><thead class="table-light"><tr>%s</tr></thead><tbody>')
                                   % Markup('').join(Markup('<th>%s</th>') % h for h in header)) + body + Markup('</tbody></table>') + note

    # ---------------------------------------------------------------- export
    def _check_dates(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise UserError(_('Tanggal awal tidak boleh melebihi tanggal akhir.'))

    def action_export(self):
        self.ensure_one()
        self._check_dates()
        if self.output_format == 'pdf':
            return self.env.ref('kopitera_master.action_report_kopitera').report_action(self)
        return self._export_xlsx()

    def _export_xlsx(self):
        if not xlsxwriter:
            raise UserError(_('Pustaka xlsxwriter tidak tersedia.'))
        header, rows = self._get_table()
        buffer = io.BytesIO()
        book = xlsxwriter.Workbook(buffer, {'in_memory': True})
        sheet = book.add_worksheet(self._title()[:31])
        bold = book.add_format({'bold': True})
        head = book.add_format({'bold': True, 'bg_color': '#E9ECEF', 'border': 1})
        cell = book.add_format({'border': 1, 'text_wrap': True, 'valign': 'top'})
        sheet.write(0, 0, 'Kopitera — ' + self._title(), bold)
        sheet.write(1, 0, self._filter_text())
        sheet.write(2, 0, _('Dibuat oleh %s pada %s') % (self.env.user.name, fields.Datetime.context_timestamp(
            self.with_context(tz=self.env.user.tz or 'Asia/Jakarta'), fields.Datetime.now()).strftime('%Y-%m-%d %H:%M')))
        for col, title in enumerate(header):
            sheet.write(4, col, title, head)
            sheet.set_column(col, col, 14 if col else 26)
        for r, row in enumerate(rows, start=5):
            for col, value in enumerate(row):
                sheet.write(r, col, value, cell)
        book.close()
        self.write({'file_data': base64.b64encode(buffer.getvalue()),
                    'file_name': 'kopitera-%s-%s.xlsx' % (self.report_type, fields.Date.context_today(self))})
        return {'type': 'ir.actions.act_url', 'target': 'self',
                'url': '/web/content/?model=%s&id=%s&field=file_data&filename_field=file_name&download=true' % (self._name, self.id)}

    def _report_context(self):
        """Data yang dipakai template QWeb PDF."""
        self.ensure_one()
        header, rows = self._get_table()
        return {'title': self._title(), 'filters': self._filter_text(), 'header': header, 'rows': rows,
                'recipes': self._recipes() if self.report_type == 'recipe' else self.env['kopitera.recipe'],
                'printed_by': self.env.user.name,
                'printed_at': fields.Datetime.context_timestamp(self.with_context(tz=self.env.user.tz or 'Asia/Jakarta'),
                                                                fields.Datetime.now()).strftime('%Y-%m-%d %H:%M')}
