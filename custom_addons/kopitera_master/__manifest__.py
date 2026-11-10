{
    'name': 'Kopitera',
    'summary': 'Menu, resep, gramasi, dan persetujuan perubahan Kopitera',
    'version': '17.0.1.1.0',
    'category': 'Operations',
    'license': 'LGPL-3',
    'depends': ['mail'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/rules.xml',
        'data/reference.xml',
        'views/kopitera_views.xml',
        'views/master_change_views.xml',
    ],
    'application': True,
    'installable': True,
}
