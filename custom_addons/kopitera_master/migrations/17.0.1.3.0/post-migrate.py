"""17.0.1.3.0: kategori & status ketersediaan menu, jumlah porsi, satuan takaran, usulan tanggal rilis."""
from odoo import SUPERUSER_ID, api

from odoo.addons.kopitera_master.hooks import fill_menu_categories


def migrate(cr, version):
    if version:
        fill_menu_categories(api.Environment(cr, SUPERUSER_ID, {}))
