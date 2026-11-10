from odoo import SUPERUSER_ID, api

from odoo.addons.kopitera_master.hooks import sync_existing_data


def migrate(cr, version):
    if version:
        sync_existing_data(api.Environment(cr, SUPERUSER_ID, {}))
