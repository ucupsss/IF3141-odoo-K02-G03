"""Provision local demonstration accounts and fictional recipe data via XML-RPC.

Run with Python from the repository root after installing kopitera_master.
Credentials are generated locally and never belong in Git.
"""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import secrets
import socket
import xmlrpc.client

socket.setdefaulttimeout(60)
root = Path(__file__).resolve().parents[1]
access = dict(line.split(': ', 1) for line in (root / 'AKSES-LOKAL.txt').read_text(encoding='utf-8').splitlines() if ': ' in line)
url = 'http://127.0.0.1:8070'
db = access['Database']
common = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/common', allow_none=True)
objects = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/object', allow_none=True)

def session(login, password):
    uid = common.authenticate(db, login, password, {})
    if not uid:
        raise RuntimeError('Authentication failed for ' + login)
    def call(model, method, args=None, **kwargs):
        return objects.execute_kw(db, uid, password, model, method, args or [], kwargs)
    return uid, call

admin_id, admin = session(access['Login'], access['Password'])

def ref(name):
    module, key = name.split('.', 1)
    found = admin('ir.model.data', 'search_read', [[['module', '=', module], ['name', '=', key]]], fields=['res_id'])
    if not found:
        raise RuntimeError('Missing XML ID: ' + name)
    return found[0]['res_id']

account_file = root / 'AKUN-UJI-LOKAL.txt'
accounts = json.loads(account_file.read_text(encoding='utf-8')) if account_file.exists() else []
role_specs = [
    ('manager', 'Manager Area', 'group_manager'),
    ('headbar', 'Head Bar — Pengaju', 'group_head_bar'),
    ('reviewerbar', 'Head Bar — Pemeriksa', 'group_head_bar'),
    ('headkitchen', 'Head Kitchen — Pengaju', 'group_head_kitchen'),
    ('reviewerkitchen', 'Head Kitchen — Pemeriksa', 'group_head_kitchen'),
    ('stafbar', 'Staf Bar', 'group_bar'),
    ('stafkitchen', 'Staf Kitchen', 'group_kitchen'),
    ('mod', 'Manager on Duty', 'group_view_all'),
    ('headfloor', 'Head Floor', 'group_view_all'),
]
for key, role, group in role_specs:
    login = key + '.kopitera'
    if any(a['login'] == login for a in accounts):
        continue
    if admin('res.users', 'search_count', [[['login', '=', login]]]):
        raise RuntimeError('Existing account has no saved password; no password was reset: ' + login)
    password = secrets.token_urlsafe(18)
    uid = admin('res.users', 'create', [{
        'name': role + ' (Uji)', 'login': login, 'password': password,
        'email': login + '@example.test', 'tz': 'Asia/Jakarta', 'lang': 'en_US',
        'notification_type': 'inbox',
        'groups_id': [(6, 0, [ref('kopitera_master.' + group)])],
    }], context={'no_reset_password': True, 'mail_create_nosubscribe': True})
    accounts.append({'peran': role, 'login': login, 'password': password, 'id': uid})
    account_file.write_text(json.dumps(accounts, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

sessions = {}
for account in accounts:
    admin('res.users', 'write', [[account['id']], {'email': account['login'] + '@example.test', 'notification_type': 'inbox'}])
    sessions[account['login'].split('.')[0]] = session(account['login'], account['password'])[1]

today = datetime.now(ZoneInfo('Asia/Jakarta')).date().isoformat()
for area, menu_xml, composition, instructions in [
    ('bar', 'menu_kopi_susu', [('coffee', 30), ('milk', 120), ('sugar', 20), ('ice', 100)],
     '1. Campurkan espresso dan sirup gula aren.\n2. Tambahkan susu cair.\n3. Masukkan es dan sajikan per porsi.\nData fiktif untuk demonstrasi.'),
    ('kitchen', 'menu_nasi_goreng', [('rice', 200), ('egg', 1), ('soy', 15)],
     '1. Masak telur hingga matang.\n2. Tambahkan nasi dan kecap.\n3. Aduk hingga tercampur dan sajikan per porsi.\nData fiktif untuk demonstrasi.'),
]:
    menu_id = ref('kopitera_master.' + menu_xml)
    author, reviewer, manager = sessions['head' + area], sessions['reviewer' + area], sessions['manager']
    if not admin('kopitera.recipe', 'search_count', [[['menu_id', '=', menu_id], ['state', '=', 'published']]]):
        existing = author('kopitera.recipe', 'search', [[['menu_id', '=', menu_id], ['reason', '=', 'Resep awal fiktif untuk demonstrasi Milestone 4.']]], limit=1)
        recipe = existing[0] if existing else author('kopitera.recipe', 'create', [{
            'menu_id': menu_id, 'reason': 'Resep awal fiktif untuk demonstrasi Milestone 4.',
            'instructions': instructions,
            'line_ids': [(0, 0, {'ingredient_id': ref('kopitera_master.ingredient_' + ingredient), 'quantity': qty}) for ingredient, qty in composition],
        }])
        state = author('kopitera.recipe', 'read', [[recipe]], fields=['state'])[0]['state']
        if state == 'draft':
            author('kopitera.recipe', 'action_submit', [[recipe]])
            state = 'review'
        if state == 'review':
            reviewer('kopitera.recipe', 'write', [[recipe], {'review_note': 'Komposisi dan takaran contoh sudah diperiksa untuk demonstrasi.'}])
            reviewer('kopitera.recipe', 'action_review', [[recipe]])
            state = 'approval'
        if state == 'approval':
            manager('kopitera.recipe', 'write', [[recipe], {'release_date': today, 'decision_note': 'Disetujui sebagai data contoh tugas, bukan resep operasional.'}])
            manager('kopitera.recipe', 'action_approve', [[recipe]])
            state = 'approved'
        if state == 'approved':
            manager('kopitera.recipe', 'action_release', [[recipe]])
    if not admin('kopitera.recipe', 'search_count', [[['menu_id', '=', menu_id], ['state', 'in', ['draft', 'revision', 'review', 'approval', 'approved']]]]):
        action = author('kopitera.menu', 'action_propose_recipe', [[menu_id]])
        author('kopitera.recipe', 'write', [[action['res_id']], {'reason': 'Latihan pengajuan perubahan resep; silakan sesuaikan takaran sebelum dikirim.'}])

print(json.dumps({'accounts_ready': len(accounts), 'published_recipes': admin('kopitera.recipe', 'search_count', [[['state', '=', 'published']]]), 'draft_recipes': admin('kopitera.recipe', 'search_count', [[['state', '=', 'draft']]])}))
