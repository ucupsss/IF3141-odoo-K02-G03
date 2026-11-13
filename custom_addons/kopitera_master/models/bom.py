"""Sinkronisasi resep berlaku ke Bill of Materials modul Manufacturing (mrp.bom).

Sumber kebenaran tetap model Kopitera, karena alur pengajuan/pemeriksaan/persetujuan berada di sana.
Setiap kali resep dirilis, BoM menu diperbarui menjadi salinan baca dari versi berlaku dan BoM versi
sebelumnya diarsipkan, sehingga data resep juga tersedia sebagai BoM standar Odoo.
"""
from odoo import fields, models, _

UOM_XMLIDS = {'g': 'uom.product_uom_gram', 'kg': 'uom.product_uom_kgm', 'ml': 'kopitera_master.uom_ml',
              'l': 'uom.product_uom_litre', 'pcs': 'uom.product_uom_unit'}


class MenuProduct(models.Model):
    _inherit = 'kopitera.menu'

    product_tmpl_id = fields.Many2one('product.template', 'Produk Manufacturing', readonly=True, copy=False,
                                      groups='base.group_system')

    def _kp_ensure_product(self):
        unit = self.env.ref('uom.product_uom_unit')
        for menu in self.sudo():
            vals = {'name': menu.name, 'active': menu.active}
            if menu.product_tmpl_id:
                menu.product_tmpl_id.with_context(active_test=False).write(vals)
            else:
                template = self.env['product.template'].sudo().create(dict(
                    vals, detailed_type='consu', sale_ok=False, purchase_ok=False, uom_id=unit.id, uom_po_id=unit.id,
                    default_code='KP-MENU-%s' % menu.id, description=_('Dikelola melalui modul Kopitera.')))
                super(MenuProduct, menu).write({'product_tmpl_id': template.id})
        return True

    def write(self, vals):
        result = super().write(vals)
        if {'name', 'active'}.intersection(vals):
            synced = self.sudo().filtered('product_tmpl_id')
            synced._kp_ensure_product()
            if vals.get('active') is False:
                self.env['mrp.bom'].sudo().search([('product_tmpl_id', 'in', synced.product_tmpl_id.ids)]).write({'active': False})
        return result


class IngredientProduct(models.Model):
    _inherit = 'kopitera.ingredient'

    product_id = fields.Many2one('product.product', 'Produk Manufacturing', readonly=True, copy=False,
                                 groups='base.group_system')

    def _kp_ensure_product(self):
        for ingredient in self.sudo():
            uom = self.env.ref(UOM_XMLIDS[ingredient.unit])
            vals = {'name': ingredient.name, 'active': ingredient.active}
            if ingredient.product_id:
                ingredient.product_id.with_context(active_test=False).write(vals)
            else:
                product = self.env['product.product'].sudo().create(dict(
                    vals, detailed_type='consu', sale_ok=False, purchase_ok=False, uom_id=uom.id, uom_po_id=uom.id,
                    default_code='KP-BAHAN-%s' % ingredient.id))
                super(IngredientProduct, ingredient).write({'product_id': product.id})
        return True

    def write(self, vals):
        result = super().write(vals)
        if {'name', 'active'}.intersection(vals):
            self.sudo().filtered('product_id')._kp_ensure_product()
        return result


class RecipeBom(models.Model):
    _inherit = 'kopitera.recipe'

    bom_id = fields.Many2one('mrp.bom', 'BoM Manufacturing', readonly=True, copy=False, groups='base.group_system')

    def _kp_sync_bom(self):
        """Jadikan versi berlaku sebagai BoM aktif menu; BoM versi lama diarsipkan."""
        Bom = self.env['mrp.bom'].sudo().with_context(active_test=False)
        for recipe in self.sudo().filtered(lambda r: r.state == 'published'):
            menu = recipe.menu_id
            menu._kp_ensure_product()
            recipe.line_ids.ingredient_id._kp_ensure_product()
            Bom.search([('product_tmpl_id', '=', menu.product_tmpl_id.id), ('active', '=', True)]).write({'active': False})
            bom = Bom.create({
                'product_tmpl_id': menu.product_tmpl_id.id, 'product_qty': 1, 'type': 'normal',
                'product_uom_id': menu.product_tmpl_id.uom_id.id,
                'code': 'Kopitera %s v%s' % (recipe.name, recipe.version),
                'bom_line_ids': [(0, 0, {'product_id': line.ingredient_id.product_id.id, 'product_qty': line.quantity,
                                         'product_uom_id': self.env.ref(UOM_XMLIDS[line.unit or line.ingredient_id.unit]).id})
                                 for line in recipe.line_ids],
            })
            recipe._transition({'bom_id': bom.id})
        return True

    def action_release(self):
        result = super().action_release()
        self._kp_sync_bom()
        return result
